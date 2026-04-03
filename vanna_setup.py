"""
vanna_setup.py

Vanna 2.0 Agent initialization for the NL2SQL Clinic system.
Uses Google Gemini via the modern google-genai SDK (not the deprecated google-generativeai).

Architecture:
  - SQLValidator      : blocks unsafe SQL before execution
  - SimpleMemoryStore : in-memory Q&A pair store with keyword search
  - VannaAgent        : orchestrates LLM + memory + DB execution
"""

import os
import re
import sqlite3
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("DB_PATH", "clinic.db")

# ---------------------------------------------------------------------------
# Database schema — injected into every LLM prompt as context
# ---------------------------------------------------------------------------
SCHEMA_CONTEXT = """
Tables in the clinic SQLite database:

patients(id, first_name, last_name, email, phone, date_of_birth, gender, city, registered_date)
  gender: 'M' or 'F'

doctors(id, name, specialization, department, phone)
  specialization examples: Dermatology, Cardiology, Orthopedics, General, Pediatrics

appointments(id, patient_id, doctor_id, appointment_date, status, notes)
  patient_id -> patients.id
  doctor_id  -> doctors.id
  status: 'Scheduled' | 'Completed' | 'Cancelled' | 'No-Show'

treatments(id, appointment_id, treatment_name, cost, duration_minutes)
  appointment_id -> appointments.id

invoices(id, patient_id, invoice_date, total_amount, paid_amount, status)
  patient_id -> patients.id
  status: 'Paid' | 'Pending' | 'Overdue'
"""

# Seed examples always loaded into memory on startup
SEED_EXAMPLES = [
    {
        "question": "How many patients do we have?",
        "sql": "SELECT COUNT(*) AS total_patients FROM patients"
    },
    {
        "question": "List all doctors and their specializations",
        "sql": "SELECT name, specialization, department FROM doctors ORDER BY name"
    },
    {
        "question": "What is the total revenue?",
        "sql": "SELECT SUM(total_amount) AS total_revenue FROM invoices"
    },
    {
        "question": "Show revenue by doctor",
        "sql": (
            "SELECT d.name, SUM(i.total_amount) AS total_revenue "
            "FROM doctors d "
            "JOIN appointments a ON d.id = a.doctor_id "
            "JOIN invoices i ON a.patient_id = i.patient_id "
            "GROUP BY d.name ORDER BY total_revenue DESC"
        )
    },
    {
        "question": "Top 5 patients by spending",
        "sql": (
            "SELECT p.first_name, p.last_name, SUM(i.total_amount) AS total_spending "
            "FROM patients p "
            "JOIN invoices i ON p.id = i.patient_id "
            "GROUP BY p.id, p.first_name, p.last_name "
            "ORDER BY total_spending DESC LIMIT 5"
        )
    },
]


# ---------------------------------------------------------------------------
# SQL Validator
# ---------------------------------------------------------------------------
class SQLValidator:
    """Ensures only safe, read-only SELECT queries reach the database."""

    _BLOCKED = [
        r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b",
        r"\bALTER\b", r"\bCREATE\b", r"\bTRUNCATE\b", r"\bEXEC\b",
        r"\bEXECUTE\b", r"\bGRANT\b", r"\bREVOKE\b", r"\bSHUTDOWN\b",
        r"\bxp_", r"\bsp_", r"sqlite_master", r"sqlite_schema",
    ]

    @classmethod
    def validate(cls, sql: str) -> tuple:
        """Return (is_valid: bool, error_message: str)."""
        if not sql or not sql.strip():
            return False, "Empty SQL query"

        cleaned = sql.upper().strip()
        if not (cleaned.startswith("SELECT") or cleaned.startswith("WITH")):
            return False, "Only SELECT queries are permitted"

        for pattern in cls._BLOCKED:
            if re.search(pattern, sql, re.IGNORECASE):
                return False, f"Blocked keyword detected: {pattern}"

        return True, ""


# ---------------------------------------------------------------------------
# Memory Store
# ---------------------------------------------------------------------------
class SimpleMemoryStore:
    """Lightweight in-memory store for question → SQL pairs."""

    def __init__(self):
        self.qa_pairs: List[Dict[str, str]] = []

    def add(self, question: str, sql: str) -> None:
        self.qa_pairs.append({"question": question, "sql": sql})

    def search(self, question: str, limit: int = 5) -> List[Dict[str, str]]:
        """Return the closest matches by keyword overlap."""
        q_words = set(question.lower().split())
        scored = []
        for pair in self.qa_pairs:
            p_words = set(pair["question"].lower().split())
            score = len(q_words & p_words)
            if score > 0:
                scored.append((score, pair))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]

    def count(self) -> int:
        return len(self.qa_pairs)


# ---------------------------------------------------------------------------
# Vanna Agent
# ---------------------------------------------------------------------------
class VannaAgent:
    """
    NL2SQL agent backed by Google Gemini (google-genai SDK) and SimpleMemoryStore.

    Public interface used by main.py and seed_memory.py:
        agent.ask(question)          -> dict with sql_query, columns, rows, message, error
        agent.add_training_data(...) -> stores a Q&A pair in memory
        agent.get_memory_count()     -> int
    """

    _SYSTEM = f"""You are an expert SQL assistant for a clinic management system (SQLite).

{SCHEMA_CONTEXT}

Rules — follow every one:
1. Output ONLY a raw SQLite SELECT query. No markdown, no explanation, no code fences.
2. Never use INSERT, UPDATE, DELETE, DROP, ALTER, EXEC, GRANT, REVOKE, SHUTDOWN.
3. Use proper JOINs when data spans multiple tables.
4. Always give columns meaningful aliases (AS ...).
5. Use COUNT/SUM/AVG where the question asks for aggregation.
6. Add ORDER BY + LIMIT for top/bottom questions.
7. Use GROUP BY whenever you aggregate.
8. Use SQLite date functions: strftime('%Y-%m', col), date('now', '-N months'), etc.
9. Never access sqlite_master or any system table."""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.memory = SimpleMemoryStore()
        self._client = None
        self._init_llm()

        # Pre-load seed examples
        for ex in SEED_EXAMPLES:
            self.memory.add(ex["question"], ex["sql"])

    def _init_llm(self) -> None:
        """Initialise the Gemini client using the modern google-genai SDK."""
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("⚠️  No GOOGLE_API_KEY found — LLM disabled, memory-only mode active.")
            return

        try:
            from google import genai
            self._client = genai.Client(api_key=api_key)
            print("✓ Google Gemini LLM initialized")
        except ImportError:
            print("⚠️  google-genai not installed. Run: pip install google-genai")
        except Exception as exc:
            print(f"⚠️  Gemini init failed: {exc}")

    def _build_prompt(self, question: str) -> str:
        """Enrich the question with similar remembered queries."""
        similar = self.memory.search(question, limit=3)
        if not similar:
            return question

        lines = [question, "", "Relevant past queries for reference:"]
        for pair in similar:
            lines.append(f"  Q: {pair['question']}")
            lines.append(f"  SQL: {pair['sql']}")
        return "\n".join(lines)

    def _call_llm(self, question: str) -> Optional[str]:
        """Call Gemini and return the cleaned SQL string, or None on failure."""
        if not self._client:
            return None

        try:
            from google.genai import types as genai_types

            response = self._client.models.generate_content(
                model="gemini-2.0-flash",
                contents=self._build_prompt(question),
                config=genai_types.GenerateContentConfig(
                    system_instruction=self._SYSTEM,
                    temperature=0.1,
                ),
            )

            raw = response.text.strip()
            # Strip markdown code fences the model might add despite instructions
            raw = re.sub(r"^```(?:sql)?\s*", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"\s*```$", "", raw)
            return raw.strip()

        except Exception as exc:
            print(f"LLM error: {exc}")
            return None

    def generate_sql(self, question: str) -> Optional[str]:
        """
        Generate SQL for a natural language question.
        Falls back to the closest memory match if the LLM is unavailable.
        """
        sql = self._call_llm(question)
        if sql:
            return sql

        # Memory fallback
        similar = self.memory.search(question, limit=1)
        if similar:
            print("ℹ️  LLM unavailable — using closest memory match.")
            return similar[0]["sql"]

        return None

    def execute_sql(self, sql: str) -> Dict[str, Any]:
        """Validate and execute SQL, returning a structured result dict."""
        is_valid, error = SQLValidator.validate(sql)
        if not is_valid:
            return {"error": error, "columns": [], "rows": [], "row_count": 0}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(sql)
            columns = [d[0] for d in cursor.description] if cursor.description else []
            rows = [list(row) for row in cursor.fetchall()]
            conn.close()
            return {"columns": columns, "rows": rows, "row_count": len(rows), "error": None}
        except Exception as exc:
            return {"error": str(exc), "columns": [], "rows": [], "row_count": 0}

    def ask(self, question: str) -> Dict[str, Any]:
        """
        End-to-end: question → SQL → execute → structured response.

        Returns:
            {
                question   : str,
                sql_query  : str | None,
                columns    : list,
                rows       : list[list],
                row_count  : int,
                message    : str,
                error      : str | None,
            }
        """
        result: Dict[str, Any] = {
            "question": question,
            "sql_query": None,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "message": "",
            "error": None,
        }

        # 1. Generate SQL
        sql = self.generate_sql(question)
        if not sql:
            result["error"] = "Could not generate SQL for this question"
            result["message"] = "I couldn't understand that question. Please try rephrasing."
            return result

        result["sql_query"] = sql

        # 2. Validate
        is_valid, err = SQLValidator.validate(sql)
        if not is_valid:
            result["error"] = err
            result["message"] = f"The generated query was blocked for safety reasons: {err}"
            return result

        # 3. Execute
        exec_result = self.execute_sql(sql)
        if exec_result.get("error"):
            result["error"] = exec_result["error"]
            result["message"] = f"Database error: {exec_result['error']}"
            return result

        result["columns"] = exec_result["columns"]
        result["rows"] = exec_result["rows"]
        result["row_count"] = exec_result["row_count"]

        # 4. Summary message
        rc = result["row_count"]
        if rc == 0:
            result["message"] = "No data found for your query."
        elif rc == 1 and len(result["columns"]) == 1:
            result["message"] = f"Result: {result['rows'][0][0]}"
        else:
            result["message"] = f"Found {rc} result(s)."

        # 5. Save successful query to memory
        self.memory.add(question, sql)

        return result

    def add_training_data(self, question: str, sql: str) -> None:
        """Store a known-good Q&A pair in memory."""
        self.memory.add(question, sql)

    def get_memory_count(self) -> int:
        """Number of Q&A pairs currently in memory."""
        return self.memory.count()


# ---------------------------------------------------------------------------
# Module-level singleton — imported by main.py and seed_memory.py
# ---------------------------------------------------------------------------
_agent_instance: Optional[VannaAgent] = None


def get_agent() -> VannaAgent:
    """Return the shared global VannaAgent, creating it on first call."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = VannaAgent(db_path=DATABASE_PATH)
    return _agent_instance


# Convenience alias so existing imports work: `from vanna_setup import agent`
agent = get_agent()


# ---------------------------------------------------------------------------
# Quick smoke-test when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n── VannaAgent smoke test ──")
    a = get_agent()

    for q in [
        "How many patients do we have?",
        "List all doctors",
        "What is the total revenue?",
    ]:
        print(f"\nQ: {q}")
        r = a.ask(q)
        print(f"   SQL  : {r.get('sql_query', 'N/A')}")
        print(f"   Msg  : {r.get('message')}")
        if r.get("error"):
            print(f"   Error: {r['error']}")
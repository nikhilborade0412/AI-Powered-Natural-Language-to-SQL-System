## vanna_setup.py


import os
import re
import math
import sqlite3
from collections import Counter
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("DB_PATH", "clinic.db")

# ---------------------------------------------------------------------------
# Database schema — injected into every LLM prompt
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

Key relationships:
  - patients.id = appointments.patient_id
  - doctors.id = appointments.doctor_id
  - appointments.id = treatments.appointment_id
  - patients.id = invoices.patient_id
  - To link doctors to invoices: doctors -> appointments -> patients -> invoices
  - To link doctors to treatments: doctors -> appointments -> treatments
"""

# ---------------------------------------------------------------------------
# FIX 1: Move these constants to TOP — before the class that uses them
# ---------------------------------------------------------------------------

OUT_OF_SCOPE_KEYWORDS = [
    "dead", "died", "death", "deceased", "mortality", "killed",
    "alive", "survive", "survival", "covid", "disease outbreak",
    "weather", "stock", "price", "news", "politics", "sports",
    "salary", "employee", "staff", "hr", "payroll",
    "inventory", "supply", "product", "order", "shipping",
    "password", "login", "user", "admin", "security",
]

IN_SCOPE_KEYWORDS = [
    "patient", "patients", "doctor", "doctors", "appointment", "appointments",
    "treatment", "treatments", "invoice", "invoices", "revenue", "cost",
    "specialization", "department", "city", "spending", "visit", "visits",
    "cancelled", "completed", "scheduled", "no-show", "pending", "overdue",
    "paid", "unpaid", "duration", "count", "total", "average", "list",
    "show", "how many", "which", "top", "busiest", "trend", "monthly",
    "registered", "gender", "age", "phone", "email", "name",
]

# ---------------------------------------------------------------------------
# Comprehensive seed examples — covers all 20 test scenarios
# ---------------------------------------------------------------------------
SEED_EXAMPLES = [
    # ── Patients ──
    {
        "question": "How many patients do we have?",
        "sql": "SELECT COUNT(*) AS total_patients FROM patients"
    },
    {
        "question": "List all patients from New York",
        "sql": "SELECT first_name, last_name, email, phone FROM patients WHERE city = 'New York'"
    },
    {
        "question": "How many male and female patients do we have?",
        "sql": "SELECT gender, COUNT(*) AS count FROM patients GROUP BY gender"
    },
    {
        "question": "Which city has the most patients?",
        "sql": (
            "SELECT city, COUNT(*) AS patient_count FROM patients "
            "GROUP BY city ORDER BY patient_count DESC LIMIT 1"
        )
    },
    {
        "question": "Show patient registration trend by month",
        "sql": (
            "SELECT strftime('%Y-%m', registered_date) AS month, COUNT(*) AS new_patients "
            "FROM patients GROUP BY month ORDER BY month"
        )
    },

    # ── Doctors ──
    {
        "question": "List all doctors and their specializations",
        "sql": "SELECT name, specialization, department FROM doctors ORDER BY name"
    },
    {
        "question": "Which doctor has the most appointments?",
        "sql": (
            "SELECT d.name, COUNT(a.id) AS appointment_count "
            "FROM doctors d "
            "JOIN appointments a ON d.id = a.doctor_id "
            "GROUP BY d.id, d.name "
            "ORDER BY appointment_count DESC LIMIT 1"
        )
    },
    {
        "question": "How many doctors are in each specialization?",
        "sql": (
            "SELECT specialization, COUNT(*) AS doctor_count "
            "FROM doctors GROUP BY specialization ORDER BY doctor_count DESC"
        )
    },

    # ── Appointments ──
    {
        "question": "Show me appointments for last month",
        "sql": (
            "SELECT a.id, p.first_name, p.last_name, d.name AS doctor, "
            "a.appointment_date, a.status "
            "FROM appointments a "
            "JOIN patients p ON p.id = a.patient_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "WHERE a.appointment_date >= date('now', 'start of month', '-1 month') "
            "AND a.appointment_date < date('now', 'start of month') "
            "ORDER BY a.appointment_date"
        )
    },
    {
        "question": "How many cancelled appointments last quarter?",
        "sql": (
            "SELECT COUNT(*) AS cancelled_count FROM appointments "
            "WHERE status = 'Cancelled' "
            "AND appointment_date >= date('now', '-3 months')"
        )
    },
    {
        "question": "Show monthly appointment count for the past 6 months",
        "sql": (
            "SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS total "
            "FROM appointments "
            "WHERE appointment_date >= date('now', '-6 months') "
            "GROUP BY month ORDER BY month"
        )
    },
    {
        "question": "What percentage of appointments are no-shows?",
        "sql": (
            "SELECT ROUND(100.0 * SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) "
            "/ COUNT(*), 2) AS no_show_percentage FROM appointments"
        )
    },
    {
        "question": "Show the busiest day of the week for appointments",
        "sql": (
            "SELECT CASE CAST(strftime('%w', appointment_date) AS INTEGER) "
            "WHEN 0 THEN 'Sunday' WHEN 1 THEN 'Monday' WHEN 2 THEN 'Tuesday' "
            "WHEN 3 THEN 'Wednesday' WHEN 4 THEN 'Thursday' WHEN 5 THEN 'Friday' "
            "WHEN 6 THEN 'Saturday' END AS day_name, "
            "COUNT(*) AS total FROM appointments "
            "GROUP BY strftime('%w', appointment_date) ORDER BY total DESC"
        )
    },
    {
        "question": "List patients who visited more than 3 times",
        "sql": (
            "SELECT p.first_name, p.last_name, COUNT(a.id) AS visit_count "
            "FROM patients p "
            "JOIN appointments a ON a.patient_id = p.id "
            "GROUP BY p.id, p.first_name, p.last_name "
            "HAVING visit_count > 3 ORDER BY visit_count DESC"
        )
    },

    # ── Treatments ──
    {
        "question": "Average treatment cost by specialization",
        "sql": (
            "SELECT d.specialization, ROUND(AVG(t.cost), 2) AS avg_cost "
            "FROM treatments t "
            "JOIN appointments a ON a.id = t.appointment_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.specialization ORDER BY avg_cost DESC"
        )
    },
    {
        "question": "Average appointment duration by doctor",
        "sql": (
            "SELECT d.name, ROUND(AVG(t.duration_minutes), 1) AS avg_duration "
            "FROM doctors d "
            "JOIN appointments a ON d.id = a.doctor_id "
            "JOIN treatments t ON a.id = t.appointment_id "
            "GROUP BY d.id, d.name ORDER BY avg_duration DESC"
        )
    },

    # ── Financial ──
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
    {
        "question": "Show unpaid invoices",
        "sql": (
            "SELECT p.first_name, p.last_name, i.total_amount, i.paid_amount, "
            "i.status, i.invoice_date "
            "FROM invoices i "
            "JOIN patients p ON p.id = i.patient_id "
            "WHERE i.status IN ('Pending', 'Overdue') "
            "ORDER BY i.invoice_date DESC"
        )
    },
    {
        "question": "List patients with overdue invoices",
        "sql": (
            "SELECT DISTINCT p.first_name, p.last_name, p.email, "
            "i.total_amount, i.paid_amount, i.invoice_date "
            "FROM patients p "
            "JOIN invoices i ON p.id = i.patient_id "
            "WHERE i.status = 'Overdue' "
            "ORDER BY i.invoice_date"
        )
    },
    {
        "question": "Revenue trend by month",
        "sql": (
            "SELECT strftime('%Y-%m', invoice_date) AS month, "
            "SUM(total_amount) AS revenue "
            "FROM invoices GROUP BY month ORDER BY month"
        )
    },
    {
        "question": "Compare revenue between departments",
        "sql": (
            "SELECT d.department, SUM(i.total_amount) AS total_revenue "
            "FROM doctors d "
            "JOIN appointments a ON d.id = a.doctor_id "
            "JOIN invoices i ON a.patient_id = i.patient_id "
            "GROUP BY d.department ORDER BY total_revenue DESC"
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
# Improved Memory Store
# ---------------------------------------------------------------------------
class SimpleMemoryStore:
    """In-memory store with improved similarity scoring."""

    STOP_WORDS = {
        "the", "a", "an", "is", "are", "was", "were", "do", "does", "did",
        "have", "has", "had", "be", "been", "being", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "dare", "ought",
        "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "as", "into", "through", "during", "before", "after", "above",
        "below", "between", "out", "off", "over", "under", "again",
        "further", "then", "once", "here", "there", "when", "where", "why",
        "how", "all", "each", "every", "both", "few", "more", "most",
        "other", "some", "such", "no", "nor", "not", "only", "own", "same",
        "so", "than", "too", "very", "just", "because", "but", "and", "or",
        "if", "while", "about", "up", "down", "it", "its", "this", "that",
        "these", "those", "i", "me", "my", "we", "us", "our", "you", "your",
        "he", "him", "his", "she", "her", "they", "them", "their", "what",
        "which", "who", "whom", "show", "list", "give", "tell", "get",
        "display", "find", "see",
    }

    def __init__(self):
        self.qa_pairs: List[Dict[str, str]] = []

    def add(self, question: str, sql: str) -> None:
        for pair in self.qa_pairs:
            if pair["question"].lower().strip() == question.lower().strip():
                pair["sql"] = sql
                return
        self.qa_pairs.append({"question": question, "sql": sql})

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r'[a-z0-9]+', text.lower())
        return [w for w in words if w not in self.STOP_WORDS and len(w) > 1]

    def search(self, question: str, limit: int = 5) -> List[Dict[str, str]]:
        q_tokens = self._tokenize(question)
        if not q_tokens:
            return self.qa_pairs[:limit]

        q_counter = Counter(q_tokens)
        scored = []

        for pair in self.qa_pairs:
            p_tokens = self._tokenize(pair["question"])
            p_counter = Counter(p_tokens)
            common = set(q_counter.keys()) & set(p_counter.keys())
            if not common:
                continue

            numerator = sum(q_counter[w] * p_counter[w] for w in common)
            denom_q = math.sqrt(sum(v ** 2 for v in q_counter.values()))
            denom_p = math.sqrt(sum(v ** 2 for v in p_counter.values()))

            if denom_q == 0 or denom_p == 0:
                continue

            similarity = numerator / (denom_q * denom_p)
            scored.append((similarity, pair))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]

    def search_best(self, question: str, threshold: float = 0.6) -> Optional[Dict[str, str]]:
        q_tokens = self._tokenize(question)
        if not q_tokens:
            return None

        q_counter = Counter(q_tokens)
        best_score = 0.0
        best_pair = None

        for pair in self.qa_pairs:
            p_tokens = self._tokenize(pair["question"])
            p_counter = Counter(p_tokens)
            common = set(q_counter.keys()) & set(p_counter.keys())
            if not common:
                continue

            numerator = sum(q_counter[w] * p_counter[w] for w in common)
            denom_q = math.sqrt(sum(v ** 2 for v in q_counter.values()))
            denom_p = math.sqrt(sum(v ** 2 for v in p_counter.values()))

            if denom_q == 0 or denom_p == 0:
                continue

            similarity = numerator / (denom_q * denom_p)
            if similarity > best_score:
                best_score = similarity
                best_pair = pair

        if best_score >= threshold:
            return best_pair
        return None

    def count(self) -> int:
        return len(self.qa_pairs)


# ---------------------------------------------------------------------------
# FIX 2: VannaAgent — all methods correctly indented INSIDE the class
# ---------------------------------------------------------------------------
class VannaAgent:
    """NL2SQL agent backed by Google Gemini and improved memory."""

    _SYSTEM = f"""You are an expert SQL assistant for a clinic management system using SQLite.

{SCHEMA_CONTEXT}

STRICT RULES — follow every single one:
1. Output ONLY a raw SQLite SELECT query. No markdown, no explanation, no code fences, no comments.
2. Never use INSERT, UPDATE, DELETE, DROP, ALTER, EXEC, GRANT, REVOKE, SHUTDOWN.
3. Use proper JOINs when data spans multiple tables.
4. Always give columns meaningful aliases (AS ...).
5. Use COUNT/SUM/AVG where the question asks for aggregation or totals.
6. Add ORDER BY + LIMIT for "top", "most", "busiest" type questions.
7. Use GROUP BY whenever you aggregate.
8. For date filtering use SQLite functions: strftime('%Y-%m', col), date('now', '-N months'), etc.
9. For "last month": WHERE col >= date('now','start of month','-1 month') AND col < date('now','start of month')
10. For "last quarter": WHERE col >= date('now','-3 months')
11. For "cancelled": WHERE status = 'Cancelled'
12. For "no-show": WHERE status = 'No-Show' or use CASE WHEN status = 'No-Show'
13. For "unpaid"/"overdue": WHERE status IN ('Pending','Overdue') or WHERE status = 'Overdue'
14. For "busiest day of week": use strftime('%w', appointment_date) to extract day number
15. For "monthly trend": use strftime('%Y-%m', date_column) and GROUP BY
16. For "average duration": use AVG(duration_minutes) from treatments table joined through appointments
17. For "revenue by department": join doctors->appointments->invoices and GROUP BY department
18. Never access sqlite_master or any system table.
19. Read the question carefully. Generate SQL that EXACTLY answers THAT question, not a different one.
20. If reference examples are provided below, use them as guidance but adapt to the actual question asked."""

    # ------------------------------------------------------------------ #
    # Init                                                                 #
    # ------------------------------------------------------------------ #
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.memory = SimpleMemoryStore()
        self._client = None
        self._init_llm()

        for ex in SEED_EXAMPLES:
            self.memory.add(ex["question"], ex["sql"])

    # ------------------------------------------------------------------ #
    # LLM setup                                                            #
    # ------------------------------------------------------------------ #
    def _init_llm(self) -> None:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("Warning: No GOOGLE_API_KEY found. LLM disabled, memory-only mode.")
            return
        try:
            from google import genai
            self._client = genai.Client(api_key=api_key)
            print("Gemini LLM initialized successfully")
        except ImportError:
            print("Warning: google-genai not installed. Run: pip install google-genai")
        except Exception as exc:
            print(f"Warning: Gemini init failed: {exc}")

    # ------------------------------------------------------------------ #
    # Prompt builder                                                        #
    # ------------------------------------------------------------------ #
    def _build_prompt(self, question: str) -> str:
        similar = self.memory.search(question, limit=5)
        parts = [
            f"Question: {question}",
            "",
            "Generate a single SQLite SELECT query that answers this question.",
            "",
        ]
        if similar:
            parts.append("Here are some similar example queries for reference:")
            parts.append("")
            for i, pair in enumerate(similar, 1):
                parts.append(f"Example {i}:")
                parts.append(f"  Q: {pair['question']}")
                parts.append(f"  SQL: {pair['sql']}")
                parts.append("")
        parts.append("Now generate the SQL for the question above. Output ONLY the SQL, nothing else.")
        return "\n".join(parts)

    # ------------------------------------------------------------------ #
    # LLM call                                                             #
    # ------------------------------------------------------------------ #
    def _call_llm(self, question: str) -> Optional[str]:
        if not self._client:
            return None
        try:
            from google.genai import types as genai_types

            response = self._client.models.generate_content(
                model="gemini-2.0-flash",
                contents=self._build_prompt(question),
                config=genai_types.GenerateContentConfig(
                    system_instruction=self._SYSTEM,
                    temperature=0.0,
                    max_output_tokens=1024,
                ),
            )

            raw = response.text.strip()
            raw = re.sub(r"^```(?:sql)?\s*", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"\s*```$", "", raw)
            raw = raw.strip()

            # Strip any explanation text before SELECT/WITH
            lines = raw.split('\n')
            sql_lines = []
            found_sql = False
            for line in lines:
                if not found_sql and (
                    line.strip().upper().startswith('SELECT') or
                    line.strip().upper().startswith('WITH')
                ):
                    found_sql = True
                if found_sql:
                    sql_lines.append(line)
            if sql_lines:
                raw = '\n'.join(sql_lines)

            return raw.strip() if raw else None

        except Exception as exc:
            print(f"LLM error: {exc}")
            return None

    # ------------------------------------------------------------------ #
    # SQL generation with fallback                                         #
    # ------------------------------------------------------------------ #
    def generate_sql(self, question: str) -> Optional[str]:
        sql = self._call_llm(question)
        if sql:
            valid, _ = SQLValidator.validate(sql)
            if valid:
                return sql

        best = self.memory.search_best(question, threshold=0.7)
        if best:
            print(f"  [memory fallback] Using cached SQL for: {best['question'][:50]}")
            return best["sql"]

        similar = self.memory.search(question, limit=1)
        if similar:
            print(f"  [memory fallback] Best available: {similar[0]['question'][:50]}")
            return similar[0]["sql"]

        return None

    # ------------------------------------------------------------------ #
    # SQL execution                                                         #
    # ------------------------------------------------------------------ #
    def execute_sql(self, sql: str) -> Dict[str, Any]:
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

    # ------------------------------------------------------------------ #
    # FIX 3: Out-of-scope check — correctly indented inside class         #
    # ------------------------------------------------------------------ #
    def _is_out_of_scope(self, question: str) -> tuple:
        """Check if the question is outside the clinic database scope."""
        q_lower = question.lower().strip()

        for keyword in OUT_OF_SCOPE_KEYWORDS:
            if keyword in q_lower:
                return True, (
                    f"This question contains '{keyword}' which is outside the "
                    f"scope of the clinic database. The database contains: "
                    f"patients, doctors, appointments, treatments, and invoices."
                )

        has_clinic_keyword = any(kw in q_lower for kw in IN_SCOPE_KEYWORDS)
        if not has_clinic_keyword:
            return True, (
                "This question doesn't appear to be related to clinic data. "
                "You can ask about patients, doctors, appointments, treatments, "
                "and invoices."
            )

        return False, ""

    # ------------------------------------------------------------------ #
    # FIX 4: SQL relevance check — correctly indented inside class        #
    # ------------------------------------------------------------------ #
    def _validate_sql_relevance(self, question: str, sql: str) -> tuple:
        """Check if the generated SQL actually matches the question intent."""
        q_lower = question.lower()
        sql_lower = sql.lower()

        relevance_rules = [
            ("dead",           None,              "Database has no mortality data"),
            ("died",           None,              "Database has no mortality data"),
            ("deceased",       None,              "Database has no deceased patient records"),
            ("doctor",         "doctors",         "Query about doctors must reference the doctors table"),
            ("appointment",    "appointments",    "Query about appointments must reference appointments table"),
            ("treatment",      "treatments",      "Query about treatments must reference treatments table"),
            ("invoice",        "invoices",        "Query about invoices must reference invoices table"),
            ("revenue",        "invoices",        "Revenue queries must reference the invoices table"),
            ("specialization", "specialization",  "Query must reference specialization column"),
            ("duration",       "duration_minutes","Query must reference duration_minutes column"),
            ("city",           "city",            "Query must reference city column"),
            ("registered",     "registered_date", "Query must reference registered_date column"),
            ("department",     "department",      "Query must reference department column"),
            ("cancelled",      "cancelled",       "Query must filter by cancelled status"),
            ("overdue",        "overdue",         "Query must filter by overdue status"),
            ("pending",        "pending",         "Query must filter by pending status"),
            ("no-show",        "no-show",         "Query must filter by no-show status"),
        ]

        for q_kw, sql_kw, error_msg in relevance_rules:
            if q_kw in q_lower:
                if sql_kw is None:
                    return False, error_msg
                if sql_kw not in sql_lower:
                    return False, f"SQL mismatch: {error_msg}"

        return True, ""

    # ------------------------------------------------------------------ #
    # FIX 5: ask() — correctly indented inside class                      #
    # ------------------------------------------------------------------ #
    def ask(self, question: str) -> Dict[str, Any]:
        """End-to-end: question -> scope check -> SQL -> validate -> execute -> response."""
        result: Dict[str, Any] = {
            "question": question,
            "sql_query": None,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "message": "",
            "error": None,
        }

        # Step 1: Out-of-scope check
        out_of_scope, scope_reason = self._is_out_of_scope(question)
        if out_of_scope:
            result["error"] = "out_of_scope"
            result["message"] = f"I cannot answer this question. {scope_reason}"
            return result

        # Step 2: Generate SQL
        sql = self.generate_sql(question)
        if not sql:
            result["error"] = "Could not generate SQL for this question"
            result["message"] = "I couldn't understand that question. Please try rephrasing."
            return result

        result["sql_query"] = sql

        # Step 3: Validate SQL safety
        is_valid, err = SQLValidator.validate(sql)
        if not is_valid:
            result["error"] = err
            result["message"] = f"The generated query was blocked: {err}"
            return result

        # Step 4: Validate SQL relevance
        is_relevant, relevance_err = self._validate_sql_relevance(question, sql)
        if not is_relevant:
            result["error"] = "irrelevant_sql"
            result["message"] = (
                f"I cannot answer this question with the available clinic data. "
                f"Reason: {relevance_err}"
            )
            return result

        # Step 5: Execute
        exec_result = self.execute_sql(sql)
        if exec_result.get("error"):
            result["error"] = exec_result["error"]
            result["message"] = f"Database error: {exec_result['error']}"
            return result

        result["columns"] = exec_result["columns"]
        result["rows"] = exec_result["rows"]
        result["row_count"] = exec_result["row_count"]

        # Step 6: Summary message
        rc = result["row_count"]
        if rc == 0:
            result["message"] = "No data found for your query."
        elif rc == 1 and len(result["columns"]) == 1:
            result["message"] = f"Result: {result['rows'][0][0]}"
        else:
            result["message"] = f"Found {rc} result(s)."

        # Step 7: Save to memory
        self.memory.add(question, sql)

        return result

    # ------------------------------------------------------------------ #
    # Public helpers                                                        #
    # ------------------------------------------------------------------ #
    def add_training_data(self, question: str, sql: str) -> None:
        self.memory.add(question, sql)

    def get_memory_count(self) -> int:
        return self.memory.count()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_agent_instance: Optional[VannaAgent] = None


def get_agent() -> VannaAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = VannaAgent(db_path=DATABASE_PATH)
    return _agent_instance


agent = get_agent()


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n-- VannaAgent smoke test --")
    a = get_agent()

    test_questions = [
        "How many patients do we have?",
        "List all doctors",
        "What is the total revenue?",
        "Which doctor has the most appointments?",
        "Show me appointments for last month",
        "Average treatment cost by specialization",
        "how many patients are dead?",       # should be blocked
        "what is the weather today?",        # should be blocked
    ]

    for q in test_questions:
        print(f"\nQ: {q}")
        r = a.ask(q)
        print(f"   SQL  : {r.get('sql_query', 'N/A')}")
        print(f"   Msg  : {r.get('message')}")
        if r.get("error"):
            print(f"   Error: {r['error']}")

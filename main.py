"""
main.py

FastAPI application for the NL2SQL Clinic chatbot.
Send a plain-English question -> get SQL results + summary back.
<<<<<<< HEAD
=======

Run with:
    uvicorn main:app --reload --port 8000
>>>>>>> e8f2899 (Updated NL2SQL project files)
"""

import os
import sqlite3
import logging
from contextlib import asynccontextmanager
<<<<<<< HEAD
from typing import Optional, List, Any
=======
from datetime import datetime
from typing import Optional, List, Any, Tuple
>>>>>>> e8f2899 (Updated NL2SQL project files)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from vanna_setup import get_agent, DATABASE_PATH, SQLValidator

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("nl2sql")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty")
        if len(v) > 500:
            raise ValueError("Question is too long (max 500 characters)")
        return v


class TrainRequest(BaseModel):
    question: str
    sql: str

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty")
<<<<<<< HEAD
=======
        if len(v) > 500:
            raise ValueError("Question too long (max 500 characters)")
>>>>>>> e8f2899 (Updated NL2SQL project files)
        return v

    @field_validator("sql")
    @classmethod
    def validate_sql(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("SQL cannot be empty")
<<<<<<< HEAD
        upper = v.upper()
        if not (upper.startswith("SELECT") or upper.startswith("WITH")):
            raise ValueError("Only SELECT/WITH queries are allowed")
=======
        upper = v.upper().lstrip()
        if not (upper.startswith("SELECT") or upper.startswith("WITH")):
            raise ValueError("Only SELECT/WITH queries are allowed")
        if len(v) > 5000:
            raise ValueError("SQL too long (max 5000 characters)")
>>>>>>> e8f2899 (Updated NL2SQL project files)
        return v


class ChatResponse(BaseModel):
<<<<<<< HEAD
    message: str
    sql_query: Optional[str] = None
    columns: Optional[List[str]] = None
    rows: Optional[List[List[Any]]] = None
    row_count: Optional[int] = None
    chart: Optional[dict] = None
    chart_type: Optional[str] = None
    error: Optional[str] = None
=======
    message:    str
    sql_query:  Optional[str]            = None
    columns:    Optional[List[str]]      = None
    rows:       Optional[List[List[Any]]] = None
    row_count:  Optional[int]            = None
    chart:      Optional[dict]           = None
    chart_type: Optional[str]            = None
    error:      Optional[str]            = None


class TrainResponse(BaseModel):
    message:      str
    memory_count: int


class SchemaResponse(BaseModel):
    tables:       dict
    total_tables: int


class HealthResponse(BaseModel):
    status:             str
    database:           str
    database_path:      str
    agent_memory_items: int
    timestamp:          str


class StatsResponse(BaseModel):
    patients:     int
    doctors:      int
    appointments: int
    treatments:   int
    invoices:     int
    total_revenue: float
    pending_invoices: int
    overdue_invoices: int
>>>>>>> e8f2899 (Updated NL2SQL project files)


class TrainResponse(BaseModel):
    message: str
    memory_count: int


class SchemaResponse(BaseModel):
    tables: dict
    total_tables: int


class HealthResponse(BaseModel):
    status: str
    database: str
    database_path: str
    agent_memory_items: int


# ---------------------------------------------------------------------------
# Chart suggestion logic
# ---------------------------------------------------------------------------

def suggest_chart(question: str, columns: List[str], rows: List[List[Any]], row_count: int) -> tuple:
    """
    Suggest an appropriate chart type based on the query results.

    Returns:
        (chart_type: str or None, chart_data: dict or None)
    """
    if not columns or not rows or row_count == 0:
        return None, None

    # Single value — no chart needed
    if row_count == 1 and len(columns) == 1:
        return None, None

    q_lower = question.lower()
    num_columns = len(columns)

    # Detect numeric columns (check first row)
    numeric_indices = []
    label_indices = []
    for i, val in enumerate(rows[0]):
        if isinstance(val, (int, float)):
            numeric_indices.append(i)
        else:
            label_indices.append(i)

    # No numeric data — no chart
    if not numeric_indices:
        return None, None

    # Trend / monthly / timeline keywords -> line chart
    trend_keywords = ["trend", "monthly", "month", "over time", "past", "timeline", "history"]
    if any(kw in q_lower for kw in trend_keywords) and row_count > 1:
        chart_type = "line"
        label_col = label_indices[0] if label_indices else 0
        value_col = numeric_indices[0]
        chart_data = {
            "labels": [str(row[label_col]) for row in rows],
            "datasets": [{
                "label": columns[value_col],
                "data": [row[value_col] for row in rows],
            }],
            "x_axis": columns[label_col],
            "y_axis": columns[value_col],
        }
        return chart_type, chart_data

    # Top / ranking / compare keywords -> bar chart
    bar_keywords = ["top", "most", "busiest", "compare", "by doctor", "by department",
                     "by city", "by specialization", "revenue by", "spending"]
    if any(kw in q_lower for kw in bar_keywords) and row_count > 1:
        chart_type = "bar"
        label_col = label_indices[0] if label_indices else 0
        value_col = numeric_indices[0]
        chart_data = {
            "labels": [str(row[label_col]) for row in rows],
            "datasets": [{
                "label": columns[value_col],
                "data": [row[value_col] for row in rows],
            }],
            "x_axis": columns[label_col],
            "y_axis": columns[value_col],
        }
        return chart_type, chart_data

    # Percentage / distribution keywords -> pie chart
    pie_keywords = ["percentage", "distribution", "breakdown", "proportion", "share"]
    if any(kw in q_lower for kw in pie_keywords) and row_count <= 10:
        chart_type = "pie"
        label_col = label_indices[0] if label_indices else 0
        value_col = numeric_indices[0]
        chart_data = {
            "labels": [str(row[label_col]) for row in rows],
            "datasets": [{
                "data": [row[value_col] for row in rows],
            }],
        }
        return chart_type, chart_data

    # Generic: 2 columns (label + number), multiple rows -> bar chart
    if num_columns == 2 and len(numeric_indices) == 1 and row_count > 1:
        chart_type = "bar"
        label_col = label_indices[0] if label_indices else 0
        value_col = numeric_indices[0]
        chart_data = {
            "labels": [str(row[label_col]) for row in rows],
            "datasets": [{
                "label": columns[value_col],
                "data": [row[value_col] for row in rows],
            }],
            "x_axis": columns[label_col],
            "y_axis": columns[value_col],
        }
        return chart_type, chart_data

    return None, None


# ---------------------------------------------------------------------------
# Chart suggestion
# ---------------------------------------------------------------------------

def _safe_numeric(val: Any) -> bool:
    """Return True if val is a non-None number."""
    return isinstance(val, (int, float)) and val is not None


def suggest_chart(
    question: str,
    columns: List[str],
    rows: List[List[Any]],
    row_count: int,
) -> Tuple[Optional[str], Optional[dict]]:
    """
    Suggest a chart type and data structure based on the query results.

    Returns:
        (chart_type, chart_data) or (None, None)
    """
    # Guard: no data or single value
    if not columns or not rows or row_count == 0:
        return None, None
    if row_count == 1 and len(columns) == 1:
        return None, None

    q_lower = question.lower()

    # Identify numeric and label columns from the first non-null row
    numeric_indices: List[int] = []
    label_indices:   List[int] = []

    # Find a representative row (skip rows with all-None)
    sample_row = rows[0]
    for candidate in rows:
        if any(v is not None for v in candidate):
            sample_row = candidate
            break

    for i, val in enumerate(sample_row):
        if _safe_numeric(val):
            numeric_indices.append(i)
        else:
            label_indices.append(i)

    # No numeric column — no chart possible
    if not numeric_indices:
        return None, None

    # Choose label column safely
    label_col = label_indices[0] if label_indices else 0
    value_col = numeric_indices[0]

    # Helper to build dataset
    def build_chart(chart_type: str, multi_dataset: bool = False) -> Tuple[str, dict]:
        labels = [str(row[label_col]) if row[label_col] is not None else "N/A"
                  for row in rows]

        if multi_dataset and len(numeric_indices) > 1:
            datasets = [
                {
                    "label": columns[idx],
                    "data": [row[idx] if row[idx] is not None else 0
                             for row in rows],
                }
                for idx in numeric_indices
            ]
        else:
            datasets = [{
                "label": columns[value_col],
                "data": [row[value_col] if row[value_col] is not None else 0
                         for row in rows],
            }]

        chart_data: dict = {
            "labels":   labels,
            "datasets": datasets,
        }
        if chart_type != "pie":
            chart_data["x_axis"] = columns[label_col]
            chart_data["y_axis"] = columns[value_col]

        return chart_type, chart_data

    # ── Rule 1: Trend / time-series → LINE ────────────────────────────
    trend_kw = [
        "trend", "monthly", "over time", "past", "timeline",
        "history", "by month", "per month", "registration",
    ]
    if any(kw in q_lower for kw in trend_kw) and row_count > 1:
        return build_chart("line")

    # ── Rule 2: Percentage / distribution → PIE ────────────────────────
    pie_kw = ["percentage", "distribution", "breakdown",
              "proportion", "share", "ratio"]
    if any(kw in q_lower for kw in pie_kw) and 2 <= row_count <= 12:
        return build_chart("pie")

    # ── Rule 3: Ranking / comparison → BAR ────────────────────────────
    bar_kw = [
        "top", "most", "busiest", "compare", "comparison",
        "by doctor", "by doctors", "by department", "by city",
        "by specialization", "by specialist", "revenue by",
        "spending", "highest", "lowest", "ranking",
    ]
    if any(kw in q_lower for kw in bar_kw) and row_count > 1:
        return build_chart("bar")

    # ── Rule 4: Day of week → BAR ─────────────────────────────────────
    if "day" in q_lower and "week" in q_lower and row_count > 1:
        return build_chart("bar")

    # ── Rule 5: Generic 2-column (label + number) → BAR ──────────────
    if len(columns) == 2 and len(numeric_indices) >= 1 and row_count > 1:
        return build_chart("bar")

    # ── Rule 6: Multi-column with multiple numeric cols → BAR ─────────
    if len(numeric_indices) > 1 and row_count > 1:
        return build_chart("bar", multi_dataset=True)

    return None, None


# ---------------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------------

def _db_connect() -> sqlite3.Connection:
    """Open a read-only connection to the clinic database."""
    if not os.path.exists(DATABASE_PATH):
        raise FileNotFoundError(f"Database not found: {DATABASE_PATH}")
    return sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True)


def _get_table_names(conn: sqlite3.Connection) -> List[str]:
    """Return all user table names (avoids sqlite_master in agent context)."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# App lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
<<<<<<< HEAD
    """Startup and shutdown logic."""
    print("=" * 50)
    print("Starting NL2SQL Clinic API...")

    # Verify database exists
    if not os.path.exists(DATABASE_PATH):
        print(f"WARNING: Database not found at {DATABASE_PATH}")
        print("Run: python setup_database.py")
    else:
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            conn.close()
            table_names = [t[0] for t in tables]
            print(f"Database: {DATABASE_PATH}")
            print(f"Tables: {', '.join(table_names)}")
        except Exception as exc:
            print(f"Database error: {exc}")

    # Warm up the agent
    agent = get_agent()
    print(f"Agent memory: {agent.get_memory_count()} Q&A pairs loaded")
    print("API ready at http://127.0.0.1:8000")
    print("=" * 50)

    yield

    print("Shutting down NL2SQL API.")
=======
    """Startup checks and agent warm-up."""
    log.info("=" * 50)
    log.info("Starting NL2SQL Clinic API...")
>>>>>>> e8f2899 (Updated NL2SQL project files)

    # Database check
    if not os.path.exists(DATABASE_PATH):
        log.warning(f"Database NOT found at: {DATABASE_PATH}")
        log.warning("Run: python setup_database.py")
    else:
        try:
            conn        = sqlite3.connect(DATABASE_PATH)
            table_names = _get_table_names(conn)

            # Quick row count check
            counts = {}
            for tbl in table_names:
                counts[tbl] = conn.execute(
                    f"SELECT COUNT(*) FROM {tbl}"
                ).fetchone()[0]
            conn.close()

            log.info(f"Database  : {DATABASE_PATH}")
            log.info(f"Tables    : {', '.join(table_names)}")
            for tbl, cnt in counts.items():
                log.info(f"  {tbl:<15}: {cnt} rows")

        except Exception as exc:
            log.error(f"Database error: {exc}")

    # Agent warm-up
    agent = get_agent()
    log.info(f"Agent memory: {agent.get_memory_count()} Q&A pairs")
    log.info("API ready at http://127.0.0.1:8000")
    log.info("=" * 50)

    yield

    log.info("Shutting down NL2SQL API.")


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="NL2SQL Clinic Chatbot",
    description=(
        "Ask plain-English questions about clinic data and get SQL results back. "
        "Supports patient, doctor, appointment, treatment, and invoice queries."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
<<<<<<< HEAD
    """API landing page with usage instructions."""
=======
    """API landing page."""
>>>>>>> e8f2899 (Updated NL2SQL project files)
    return {
        "message": "NL2SQL Clinic API is running",
        "version": "2.0.0",
        "endpoints": {
<<<<<<< HEAD
            "POST /chat": "Ask a natural language question",
            "POST /train": "Add a question-SQL training pair",
            "GET /health": "Check API and database status",
            "GET /schema": "View database schema information",
            "GET /examples": "View example questions you can ask",
        },
        "example": {
            "method": "POST",
            "url": "/chat",
            "body": {"question": "How many patients do we have?"},
=======
            "POST /chat":   "Ask a natural language question",
            "POST /train":  "Add a question-SQL training pair",
            "GET  /health": "API and database status",
            "GET  /schema": "Database schema with column details",
            "GET  /stats":  "Quick summary statistics",
            "GET  /examples": "Example questions by category",
        },
        "quick_start": {
            "method": "POST",
            "url":    "/chat",
            "body":   {"question": "How many patients do we have?"},
>>>>>>> e8f2899 (Updated NL2SQL project files)
        },
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verify the API, database, and agent are operational."""
    db_status = "disconnected"
<<<<<<< HEAD

=======
>>>>>>> e8f2899 (Updated NL2SQL project files)
    try:
        if os.path.exists(DATABASE_PATH):
            conn = sqlite3.connect(DATABASE_PATH)
            conn.execute("SELECT 1")
            conn.close()
            db_status = "connected"
        else:
            db_status = f"not found: {DATABASE_PATH}"
    except Exception as exc:
        db_status = f"error: {exc}"

    agent = get_agent()
<<<<<<< HEAD

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        database=db_status,
        database_path=DATABASE_PATH,
        agent_memory_items=agent.get_memory_count(),
    )


@app.get("/schema", response_model=SchemaResponse)
async def get_schema():
    """Return the database schema — table names, columns, and row counts."""
=======
    return HealthResponse(
        status             = "ok" if db_status == "connected" else "degraded",
        database           = db_status,
        database_path      = DATABASE_PATH,
        agent_memory_items = agent.get_memory_count(),
        timestamp          = datetime.now().isoformat(),
    )


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Return quick summary statistics from the database."""
>>>>>>> e8f2899 (Updated NL2SQL project files)
    if not os.path.exists(DATABASE_PATH):
        raise HTTPException(status_code=503, detail="Database not found")

    try:
        conn = sqlite3.connect(DATABASE_PATH)
<<<<<<< HEAD
        cursor = conn.cursor()

        # Get all table names
        tables_raw = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()

        tables = {}
        for (table_name,) in tables_raw:
            # Get column info
            col_info = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
            columns = [
                {"name": col[1], "type": col[2], "nullable": not col[3], "primary_key": bool(col[5])}
                for col in col_info
            ]

            # Get row count
            row_count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

            tables[table_name] = {
                "columns": columns,
=======

        def count(table: str, where: str = "") -> int:
            q = f"SELECT COUNT(*) FROM {table}"
            if where:
                q += f" WHERE {where}"
            return conn.execute(q).fetchone()[0]

        def scalar(query: str) -> float:
            result = conn.execute(query).fetchone()[0]
            return round(float(result), 2) if result is not None else 0.0

        stats = StatsResponse(
            patients         = count("patients"),
            doctors          = count("doctors"),
            appointments     = count("appointments"),
            treatments       = count("treatments"),
            invoices         = count("invoices"),
            total_revenue    = scalar("SELECT SUM(total_amount) FROM invoices"),
            pending_invoices = count("invoices", "status = 'Pending'"),
            overdue_invoices = count("invoices", "status = 'Overdue'"),
        )
        conn.close()
        return stats

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Stats error: {exc}")


@app.get("/schema", response_model=SchemaResponse)
async def get_schema():
    """Return the full database schema with column types and row counts."""
    if not os.path.exists(DATABASE_PATH):
        raise HTTPException(status_code=503, detail="Database not found")

    try:
        conn        = sqlite3.connect(DATABASE_PATH)
        table_names = _get_table_names(conn)
        tables      = {}

        for table_name in table_names:
            col_info = conn.execute(
                f"PRAGMA table_info({table_name})"
            ).fetchall()
            columns = [
                {
                    "name":        col[1],
                    "type":        col[2],
                    "nullable":    not bool(col[3]),
                    "primary_key": bool(col[5]),
                }
                for col in col_info
            ]
            row_count = conn.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]

            tables[table_name] = {
                "columns":   columns,
>>>>>>> e8f2899 (Updated NL2SQL project files)
                "row_count": row_count,
            }

        conn.close()
<<<<<<< HEAD

=======
>>>>>>> e8f2899 (Updated NL2SQL project files)
        return SchemaResponse(tables=tables, total_tables=len(tables))

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Schema error: {exc}")


@app.get("/examples")
async def get_examples():
<<<<<<< HEAD
    """Return example questions the user can ask."""
    return {
        "examples": [
            {"category": "Patients", "questions": [
                "How many patients do we have?",
                "Which city has the most patients?",
                "Show patient registration trend by month",
            ]},
            {"category": "Doctors", "questions": [
                "List all doctors and their specializations",
                "Which doctor has the most appointments?",
            ]},
            {"category": "Appointments", "questions": [
                "Show me appointments for last month",
                "How many cancelled appointments last quarter?",
                "What percentage of appointments are no-shows?",
                "Show the busiest day of the week for appointments",
            ]},
            {"category": "Treatments", "questions": [
                "Average treatment cost by specialization",
                "Average appointment duration by doctor",
            ]},
            {"category": "Financial", "questions": [
                "What is the total revenue?",
                "Show revenue by doctor",
                "Top 5 patients by spending",
                "Show unpaid invoices",
                "Revenue trend by month",
                "Compare revenue between departments",
            ]},
=======
    """Return categorized example questions."""
    return {
        "examples": [
            {
                "category": "Patients",
                "questions": [
                    "How many patients do we have?",
                    "How many patients are there?",
                    "Which city has the most patients?",
                    "Show patients by city",
                    "Show patient registration trend by month",
                    "List all patients from New York",
                ],
            },
            {
                "category": "Doctors",
                "questions": [
                    "How many doctors are there?",
                    "List all doctors and their specializations",
                    "Which doctor has the most appointments?",
                    "How many doctors are in each specialization?",
                ],
            },
            {
                "category": "Appointments",
                "questions": [
                    "Show me appointments for last month",
                    "How many cancelled appointments last quarter?",
                    "What percentage of appointments are no-shows?",
                    "Show the busiest day of the week for appointments",
                    "Show monthly appointment count for the past 6 months",
                    "List patients who visited more than 3 times",
                ],
            },
            {
                "category": "Treatments",
                "questions": [
                    "Average treatment cost by specialization",
                    "Average appointment duration by doctor",
                    "What treatments are available?",
                    "Most expensive treatments",
                ],
            },
            {
                "category": "Financial",
                "questions": [
                    "What is the total revenue?",
                    "Show revenue by doctor",
                    "Top 5 patients by spending",
                    "Show unpaid invoices",
                    "List patients with overdue invoices",
                    "Revenue trend by month",
                    "Compare revenue between departments",
                    "Total outstanding amount",
                ],
            },
>>>>>>> e8f2899 (Updated NL2SQL project files)
        ]
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Convert a natural-language question to SQL, execute it, and return results.

    Request body:
        { "question": "Show me the top 5 patients by total spending" }
<<<<<<< HEAD

    Response includes SQL query, tabular results, summary message,
    and an optional chart suggestion for visualization.
=======
>>>>>>> e8f2899 (Updated NL2SQL project files)
    """
    log.info(f"CHAT  Q: {request.question}")

    try:
        agent  = get_agent()
        result = agent.ask(request.question)

<<<<<<< HEAD
        # Build base response
        response = ChatResponse(
            message=result["message"],
            sql_query=result.get("sql_query"),
            columns=result.get("columns"),
            rows=result.get("rows"),
            row_count=result.get("row_count"),
            error=result.get("error"),
        )

        # Suggest chart if we have valid results
        if not result.get("error") and result.get("columns") and result.get("rows"):
            chart_type, chart_data = suggest_chart(
                question=request.question,
                columns=result["columns"],
                rows=result["rows"],
                row_count=result.get("row_count", 0),
            )
            if chart_type:
                response.chart_type = chart_type
                response.chart = chart_data

=======
        # Sanitise error message — don't leak internal details
        error_msg = result.get("error")
        if error_msg and error_msg not in ("out_of_scope", "irrelevant_sql",
                                           "no_sql_generated"):
            # Internal DB / LLM error — log full detail, return generic message
            log.error(f"Internal error: {error_msg}")
            error_msg = "An internal error occurred. Please try again."

        response = ChatResponse(
            message   = result["message"],
            sql_query = result.get("sql_query"),
            columns   = result.get("columns") or [],
            rows      = result.get("rows") or [],
            row_count = result.get("row_count", 0),
            error     = error_msg,
        )

        # Chart suggestion (only on successful queries)
        if (not result.get("error")
                and result.get("columns")
                and result.get("rows")):
            chart_type, chart_data = suggest_chart(
                question  = request.question,
                columns   = result["columns"],
                rows      = result["rows"],
                row_count = result.get("row_count", 0),
            )
            if chart_type:
                response.chart_type = chart_type
                response.chart      = chart_data

        log.info(
            f"CHAT  A: rows={result.get('row_count', 0)} "
            f"error={result.get('error', 'none')}"
        )
>>>>>>> e8f2899 (Updated NL2SQL project files)
        return response

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        log.exception(f"Unhandled error in /chat: {exc}")
        return ChatResponse(
<<<<<<< HEAD
            message="Something went wrong while processing your question.",
            error=str(exc),
=======
            message = "Something went wrong. Please try again.",
            error   = "server_error",
>>>>>>> e8f2899 (Updated NL2SQL project files)
        )


@app.post("/train", response_model=TrainResponse)
async def train(request: TrainRequest):
    """
    Add a known-good question-SQL pair to the agent's memory.

<<<<<<< HEAD
    This improves future responses for similar questions.

    Request body:
        {
            "question": "How many patients are from Chicago?",
            "sql": "SELECT COUNT(*) FROM patients WHERE city = 'Chicago'"
        }
    """
    try:
        agent = get_agent()
        agent.add_training_data(request.question, request.sql)

        return TrainResponse(
            message=f"Training pair added successfully",
            memory_count=agent.get_memory_count(),
        )

    except Exception as exc:
=======
    Request body:
        {
            "question": "How many patients are from Chicago?",
            "sql": "SELECT COUNT(*) AS count FROM patients WHERE city = 'Chicago'"
        }
    """
    log.info(f"TRAIN Q: {request.question[:60]}")

    try:
        # Validate SQL is safe before adding
        is_valid, err = SQLValidator.validate(request.sql)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid SQL: {err}"
            )

        agent = get_agent()

        # Check for duplicate (memory store deduplicates, but give feedback)
        before = agent.get_memory_count()
        agent.add_training_data(request.question, request.sql)
        after  = agent.get_memory_count()

        if after > before:
            msg = "Training pair added successfully"
        else:
            msg = "Training pair updated (question already existed)"

        log.info(f"TRAIN result: {msg} — memory={after}")
        return TrainResponse(message=msg, memory_count=after)

    except HTTPException:
        raise
    except Exception as exc:
        log.exception(f"Training error: {exc}")
>>>>>>> e8f2899 (Updated NL2SQL project files)
        raise HTTPException(status_code=500, detail=f"Training error: {exc}")


# ---------------------------------------------------------------------------
<<<<<<< HEAD
# Run directly with: python main.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
=======
# Run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
>>>>>>> e8f2899 (Updated NL2SQL project files)

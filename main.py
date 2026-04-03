"""
main.py

FastAPI application for the NL2SQL Clinic chatbot.
Send a plain-English question -> get SQL results + summary back.

Run with:
    uvicorn main:app --reload --port 8000
"""

import os
import sqlite3
from contextlib import asynccontextmanager
from typing import Optional, List, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from vanna_setup import get_agent, DATABASE_PATH


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
        return v

    @field_validator("sql")
    @classmethod
    def validate_sql(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("SQL cannot be empty")
        upper = v.upper()
        if not (upper.startswith("SELECT") or upper.startswith("WITH")):
            raise ValueError("Only SELECT/WITH queries are allowed")
        return v


class ChatResponse(BaseModel):
    message: str
    sql_query: Optional[str] = None
    columns: Optional[List[str]] = None
    rows: Optional[List[List[Any]]] = None
    row_count: Optional[int] = None
    chart: Optional[dict] = None
    chart_type: Optional[str] = None
    error: Optional[str] = None


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
# App setup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
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
    """API landing page with usage instructions."""
    return {
        "message": "NL2SQL Clinic API is running",
        "version": "2.0.0",
        "endpoints": {
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
        },
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verify the API, database, and agent are operational."""
    db_status = "disconnected"

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

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        database=db_status,
        database_path=DATABASE_PATH,
        agent_memory_items=agent.get_memory_count(),
    )


@app.get("/schema", response_model=SchemaResponse)
async def get_schema():
    """Return the database schema — table names, columns, and row counts."""
    if not os.path.exists(DATABASE_PATH):
        raise HTTPException(status_code=503, detail="Database not found")

    try:
        conn = sqlite3.connect(DATABASE_PATH)
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
                "row_count": row_count,
            }

        conn.close()

        return SchemaResponse(tables=tables, total_tables=len(tables))

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Schema error: {exc}")


@app.get("/examples")
async def get_examples():
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
        ]
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Convert a natural-language question to SQL, execute it, and return results.

    Request body:
        { "question": "Show me the top 5 patients by total spending" }

    Response includes SQL query, tabular results, summary message,
    and an optional chart suggestion for visualization.
    """
    try:
        agent = get_agent()
        result = agent.ask(request.question)

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

        return response

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        return ChatResponse(
            message="Something went wrong while processing your question.",
            error=str(exc),
        )


@app.post("/train", response_model=TrainResponse)
async def train(request: TrainRequest):
    """
    Add a known-good question-SQL pair to the agent's memory.

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
        raise HTTPException(status_code=500, detail=f"Training error: {exc}")


# ---------------------------------------------------------------------------
# Run directly with: python main.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

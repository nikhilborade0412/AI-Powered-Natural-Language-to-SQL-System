"""
main.py

FastAPI application for the NL2SQL Clinic chatbot.
Send a plain-English question → get SQL results + summary back.

Run with:
    uvicorn main:app --reload --port 8000
"""

import sqlite3
from contextlib import asynccontextmanager
from typing import Optional

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


class ChatResponse(BaseModel):
    message: str
    sql_query: Optional[str] = None
    columns: Optional[list] = None
    rows: Optional[list] = None
    row_count: Optional[int] = None
    chart: Optional[dict] = None
    chart_type: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting NL2SQL API...")
    get_agent()          # warm up the singleton on startup
    yield
    print("Shutting down NL2SQL API.")


app = FastAPI(
    title="NL2SQL Clinic Chatbot",
    description="Ask plain-English questions about clinic data and get SQL results back.",
    version="1.0.0",
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
    return {"message": "NL2SQL Clinic API is running. Use POST /chat to ask questions."}


@app.get("/health")
async def health_check():
    """Verify the API and database are operational."""
    db_status = "connected"
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.execute("SELECT 1")
        conn.close()
    except Exception as exc:
        db_status = f"error: {exc}"

    agent = get_agent()
    return {
        "status": "ok",
        "database": db_status,
        "agent_memory_items": agent.get_memory_count(),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Convert a natural-language question to SQL, execute it, and return results.

    Request body:
        { "question": "Show me the top 5 patients by total spending" }

    Response:
        {
            "message":   "Found 5 result(s).",
            "sql_query": "SELECT ...",
            "columns":   ["first_name", "last_name", "total_spending"],
            "rows":      [["Alice", "Smith", 4500.0], ...],
            "row_count": 5,
            "error":     null
        }
    """
    try:
        agent = get_agent()
        result = agent.ask(request.question)

        return ChatResponse(
            message=result["message"],
            sql_query=result.get("sql_query"),
            columns=result.get("columns"),
            rows=result.get("rows"),
            row_count=result.get("row_count"),
            error=result.get("error"),
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        return ChatResponse(
            message="Something went wrong while processing your question.",
            error=str(exc),
        )
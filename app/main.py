from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.db import log_query, recent_queries
from app.rag import answer

app = FastAPI(title="RAG Agent")


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]


class HistoryItem(BaseModel):
    question: str
    answer: str
    sources: list[str]
    created_at: datetime


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    result = answer(request.question)
    log_query(request.question, result["answer"], result["sources"])
    return result


@app.get("/history", response_model=list[HistoryItem])
def history(limit: int = 10):
    return recent_queries(limit)


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")

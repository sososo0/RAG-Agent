from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.rag import answer

app = FastAPI(title="RAG Agent")


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    return answer(request.question)


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")

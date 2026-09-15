"""FastAPI backend exposing POST /query."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# React dev server default port. Update if the frontend (Giai đoạn 8) runs
# elsewhere, and again for the deployed frontend origin once that exists.
FRONTEND_ORIGINS = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    sql: str
    rows: list
    explanation: str | None = None


# TODO: POST /query -> self_correct.answer_question, mapping exceptions to HTTP status codes

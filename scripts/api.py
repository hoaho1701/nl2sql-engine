"""Giai đoạn 8 — FastAPI backend.

Xem PROGRESS.md Giai đoạn 8: CORS cho origin của frontend React, map
exception (UnsafeQueryError -> 400, QueryTimeoutError -> 408, khác -> 500).
"""

from fastapi import FastAPI

app = FastAPI()

# TODO: app.add_middleware(CORSMiddleware, allow_origins=[...])

# TODO: Pydantic models cho request (QueryRequest: question: str) và
# response (QueryResponse: sql: str, rows: list, explanation: str | None)

# TODO: @app.post("/query") -> self_correct.answer_question(question) ->
# map SqlExecutionError subclasses sang đúng HTTP status code

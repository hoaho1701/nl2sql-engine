"""FastAPI backend exposing POST /query."""

import logging
from typing import Annotated

import openai
import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, StringConstraints

from app.self_correct import answer_question
from app.sql_executor import QueryTimeoutError, SqlExecutionError, UnsafeQueryError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

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
    # Whitespace is stripped first, so a blank question is rejected before the model is called.
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class QueryResponse(BaseModel):
    sql: str
    columns: list[str]
    rows: list
    attempts: int
    explanation: str | None = None


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    try:
        answer = answer_question(request.question)
    except UnsafeQueryError as e:
        logger.warning("query rejected: %s", e)
        raise HTTPException(
            status_code=400,
            detail="The question asks for something that is not allowed. Only read-only queries are supported.",
        )
    except QueryTimeoutError as e:
        logger.warning("query timed out: %s", e)
        raise HTTPException(status_code=504, detail="The query took too long to run.")
    except SqlExecutionError as e:
        logger.warning("could not build a working query: %s", e)
        raise HTTPException(
            status_code=422,
            detail="Could not build a working query for this question.",
        )
    except (openai.APIConnectionError, psycopg2.OperationalError):
        logger.exception("a required service is unavailable")
        raise HTTPException(
            status_code=503,
            detail="A required service is unavailable. Please try again later.",
        )

    return QueryResponse(sql=answer.sql, columns=answer.columns, rows=answer.rows, attempts=len(answer.attempts))

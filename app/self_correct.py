"""Self-correction loop: retry SQL generation with the execution error fed back to the LLM."""

import logging
from dataclasses import dataclass

from app.llm_sql import generate_sql
from app.sql_executor import (
    QueryTimeoutError,
    SqlExecutionError,
    UnsafeQueryError,
    run_sql_safe,
)

logger = logging.getLogger(__name__)

# Timeouts and rejected queries rarely improve with repeated rewrites, so each kind of
# error gets this many retries at most, whatever max_retries is.
MAX_RETRIES_PER_KIND = 1


@dataclass
class Attempt:
    """One try: the SQL the model wrote and the error it caused (None if it ran)."""

    sql: str
    error: str | None


@dataclass
class Answer:
    """The SQL that finally ran, its result, and every attempt made on the way."""

    sql: str
    columns: list[str]
    rows: list[tuple]
    attempts: list[Attempt]


def _build_feedback(sql: str, error: SqlExecutionError) -> list[dict]:
    """Chat messages that show the model its failed SQL and say how to fix it."""
    if isinstance(error, QueryTimeoutError):
        message = (
            "That query ran past the time limit and was cancelled. Rewrite it to be "
            "cheaper: avoid correlated subqueries, aggregate before joining, and "
            "select only the columns you need. Return only the corrected SQL."
        )
    elif isinstance(error, UnsafeQueryError):
        message = (
            f"That query was rejected: {error}\n"
            "Return a single read-only SELECT statement and nothing else."
        )
    else:
        message = (
            f"That query failed with this PostgreSQL error:\n{error}\n"
            "Return only the corrected SQL."
        )
    return [
        {"role": "assistant", "content": sql},
        {"role": "user", "content": message},
    ]


def answer_question(question: str, max_retries: int = 2, max_rows: int = 100) -> Answer:
    """generate_sql -> run_sql_safe; on failure, retry with the bad SQL and the error fed back
    to the model, up to max_retries times. Log each attempt. max_rows caps the rows fetched.

    Retry rules:
    - total attempts are at most max_retries + 1, shared across all kinds of error
    - QueryTimeoutError and UnsafeQueryError get at most one retry each
    - stop early if the model returns the SQL that just failed
    - only SqlExecutionError is retried; any other exception propagates
    - when giving up, raise the last error
    """
    if max_retries < 0:
        raise ValueError("max_retries must be >= 0")

    feedback = None
    attempts: list[Attempt] = []
    last_sql = None
    last_error = None
    retried = {QueryTimeoutError: 0, UnsafeQueryError: 0}

    for _ in range(max_retries + 1):
        sql = generate_sql(question, feedback)
        if sql.strip() == last_sql:
            # The model repeated the SQL that just failed; running it again cannot help.
            raise last_error
        try:
            columns, rows = run_sql_safe(sql, max_rows=max_rows)
        except SqlExecutionError as e:
            attempts.append(Attempt(sql, str(e)))
            logger.warning("attempt %d failed: %s", len(attempts), e)
            for kind in retried:
                if isinstance(e, kind):
                    if retried[kind] >= MAX_RETRIES_PER_KIND:
                        raise
                    retried[kind] += 1
            last_sql, last_error = sql.strip(), e
            feedback = _build_feedback(sql, e)
        else:
            attempts.append(Attempt(sql, None))
            logger.info("attempt %d succeeded", len(attempts))
            return Answer(sql, columns, rows, attempts)
    raise last_error

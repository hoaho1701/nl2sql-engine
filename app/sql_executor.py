"""Execute LLM-generated SQL safely against Postgres (defense in depth, independent layers)."""

import os
import sqlparse
import psycopg2

from dotenv import load_dotenv
from app.vector_store import REPO_ROOT


class SqlExecutionError(Exception):
    """Base exception for the execution layer."""


class UnsafeQueryError(SqlExecutionError):
    """Not a single SELECT statement."""


class QueryTimeoutError(SqlExecutionError):
    """Query exceeded statement_timeout."""


def _is_select_only(sql: str) -> bool:
    """Layer 1: reject anything not starting with "select" or "with" (CTE) after
    strip().lower().

    Known gap: a WITH clause can contain a data-modifying CTE, e.g.
    `WITH x AS (DELETE FROM orders RETURNING *) SELECT * FROM x` — this is a
    read-only-looking statement that actually deletes rows. No string-level
    check (including sqlparse's get_type(), which reports "SELECT" for this
    exact query since it only looks at the outer statement) can catch this
    reliably. This layer intentionally allows it through; layer 2 (read-only
    DB role) is the real backstop for this case.
    """
    normalized = sql.strip().lower()
    return normalized.startswith("select") or normalized.startswith("with")


def _is_single_statement(sql: str) -> bool:
    """Layer 3: count statements via sqlparse.parse(sql); reject if more than one."""
    statements = sqlparse.parse(sql)
    return len(statements) == 1


def run_sql_safe(sql: str, max_rows: int = 100, timeout_seconds: float = 5.0):
    """Layer 1 -> layer 2 (connect as read-only role, SET statement_timeout) -> layer 3 ->
    cursor.fetchmany(max_rows). Catch psycopg2.errors.QueryCanceled -> QueryTimeoutError.

    Returns (columns, rows): column names as a list, rows as a list of tuples.
    """
    if not _is_select_only(sql):
        raise UnsafeQueryError("Only SELECT or WITH queries are allowed.")

    if not _is_single_statement(sql):
        raise UnsafeQueryError("Only a single SQL statement is allowed.")

    load_dotenv(REPO_ROOT / ".env")

    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_READONLY_USER"],
        password=os.environ["POSTGRES_READONLY_PASSWORD"],
        options=f"-c statement_timeout={int(timeout_seconds * 1000)}"
    )

    try:
        cur = conn.cursor()
        cur.execute(sql)
        if cur.description is None:
            raise SqlExecutionError("The statement did not return any rows.")
        columns = [col.name for col in cur.description]
        rows = cur.fetchmany(max_rows)
        return (columns, rows)
    except psycopg2.errors.QueryCanceled as e:
        raise QueryTimeoutError(f"Query exceeded the {timeout_seconds} s time limit.") from e
    except psycopg2.errors.InsufficientPrivilege as e:
        raise UnsafeQueryError(f"Blocked by database permissions: {e}") from e
    except psycopg2.Error as e:
        raise SqlExecutionError(str(e)) from e
    finally:
        conn.close()
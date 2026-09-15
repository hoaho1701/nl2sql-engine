"""Execute LLM-generated SQL safely against Postgres (defense in depth, independent layers)."""

import sqlparse


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
    cursor.fetchmany(max_rows). Catch psycopg2.errors.QueryCanceled -> QueryTimeoutError."""
    raise NotImplementedError

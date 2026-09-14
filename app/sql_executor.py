"""Execute LLM-generated SQL safely against Postgres (defense in depth, independent layers)."""


class SqlExecutionError(Exception):
    """Base exception for the execution layer."""


class UnsafeQueryError(SqlExecutionError):
    """Not a single SELECT statement."""


class QueryTimeoutError(SqlExecutionError):
    """Query exceeded statement_timeout."""


def _is_select_only(sql: str) -> bool:
    """Layer 1: reject anything not starting with "select" after strip().lower()."""
    raise NotImplementedError


def _is_single_statement(sql: str) -> bool:
    """Layer 3: count statements via sqlparse.parse(sql); reject if more than one."""
    raise NotImplementedError


def run_sql_safe(sql: str, max_rows: int = 100, timeout_seconds: float = 5.0):
    """Layer 1 -> layer 2 (connect as read-only role, SET statement_timeout) -> layer 3 ->
    cursor.fetchmany(max_rows). Catch psycopg2.errors.QueryCanceled -> QueryTimeoutError."""
    raise NotImplementedError

import sqlite3
import time
from schema_context import DB_PATH

MAX_ROWS = 100
TIMEOUT_SECONDS = 5.0


class SqlExecutionError(Exception):
    """Base class so callers can catch every failure mode from run_sql_safe() at once."""
    pass


class UnsafeQueryError(SqlExecutionError):
    """Query failed the SELECT-only / single-statement check."""
    pass


class QueryTimeoutError(SqlExecutionError):
    """Query was interrupted for running past timeout_seconds."""
    pass


def _is_select_only(sql: str) -> bool:
    return sql.strip().lower().startswith("select")


def run_sql_safe(sql: str, max_rows: int = MAX_ROWS, timeout_seconds: float = TIMEOUT_SECONDS):
    if not _is_select_only(sql):
        raise UnsafeQueryError("Only SELECT statements are allowed")

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    try:
        deadline = time.monotonic() + timeout_seconds

        def check_timeout():
            if time.monotonic() > deadline:
                return 1  # Non-zero value aborts the query execution in SQLite
            return 0

        conn.set_progress_handler(check_timeout, 1000)

        try:
            cur = conn.execute(sql)
            rows = cur.fetchmany(max_rows)
        except sqlite3.ProgrammingError as e:
            # sqlite3 itself refuses to run more than one statement per execute() call.
            raise UnsafeQueryError(f"Only a single SQL statement is allowed: {e}") from e
        except sqlite3.OperationalError as e:
            # The progress handler aborts a query by raising this same exception type,
            # so the deadline check is what distinguishes a real timeout from any other
            # operational error (e.g. a genuine syntax/reference mistake in the SQL).
            if time.monotonic() >= deadline:
                raise QueryTimeoutError(f"Query exceeded {timeout_seconds}s timeout") from e
            raise

        columns = [d[0] for d in cur.description] if cur.description else []

        return columns, rows
    finally:
        conn.close()


if __name__ == "__main__":
    tests = [
        ("normal select", "SELECT * FROM orders LIMIT 5", {}),
        ("limit enforced on big table", "SELECT * FROM order_items", {"max_rows": 10}),
        ("lowercase + whitespace", "  \nselect 1", {}),
        ("delete blocked", "DELETE FROM orders", {}),
        ("stacked query", "SELECT 1; DROP TABLE orders;", {}),
        ("orders still intact after stacked attempt", "SELECT COUNT(*) FROM orders", {}),
        ("timeout on slow aggregate", "SELECT COUNT(*) FROM order_items a, order_items b", {"timeout_seconds": 1}),
    ]

    for label, sql, kwargs in tests:
        try:
            result = run_sql_safe(sql, **kwargs)
            print(f"[{label}] OK -> {result}")
        except Exception as e:
            print(f"[{label}] {type(e).__name__}: {e}")

"""Tests for run_sql_safe against the real Postgres, ordered from easiest to hardest."""

import os
import time

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.load_data import get_engine
from app.sql_executor import (
    QueryTimeoutError,
    SqlExecutionError,
    UnsafeQueryError,
    run_sql_safe,
)


def _database_is_up() -> bool:
    try:
        with get_engine().connect():
            return True
    except OperationalError:
        return False


pytestmark = pytest.mark.skipif(not _database_is_up(), reason="Postgres is not running")


def _open_readonly_connections() -> int:
    """Count open connections of the read-only role, as the superuser."""
    with get_engine().connect() as conn:
        return conn.execute(
            text("SELECT count(*) FROM pg_stat_activity WHERE usename = :name"),
            {"name": os.environ["POSTGRES_READONLY_USER"]},
        ).scalar_one()


def _orders_count() -> int:
    """Count orders as the superuser, independent of the code under test."""
    with get_engine().connect() as conn:
        return conn.execute(text("SELECT count(*) FROM orders")).scalar_one()


# Connect as the read-only role and read data.
def test_select_returns_columns_and_rows():
    columns, rows = run_sql_safe("SELECT count(*) AS n FROM orders")
    assert columns == ["n"]
    assert rows == [(_orders_count(),)]


# Layer 1 rejects non-SELECT before touching the database.
def test_delete_is_rejected_and_data_is_intact():
    before = _orders_count()
    assert before > 0
    with pytest.raises(UnsafeQueryError):
        run_sql_safe("DELETE FROM orders")
    assert _orders_count() == before


# Cap the rows pulled into Python.
def test_row_limit_caps_rows_fetched():
    _, rows = run_sql_safe("SELECT * FROM generate_series(1, 100)", max_rows=5)
    assert len(rows) == 5


# Stacked queries are rejected by the statement-count layer.
def test_stacked_query_is_rejected_and_data_is_intact():
    before = _orders_count()
    assert before > 0
    with pytest.raises(UnsafeQueryError):
        run_sql_safe("SELECT 1; DROP TABLE orders")
    assert _orders_count() == before


# A slow query is cut off by statement_timeout.
def test_slow_query_raises_timeout_quickly():
    start = time.monotonic()
    with pytest.raises(QueryTimeoutError):
        run_sql_safe("SELECT pg_sleep(5)", timeout_seconds=0.5)
    assert time.monotonic() - start < 2


# Ordinary SQL errors are reported, with the Postgres message kept.
def test_sql_error_is_wrapped_and_keeps_the_original_message():
    with pytest.raises(SqlExecutionError) as excinfo:
        run_sql_safe("SELECT nope FROM orders")
    assert not isinstance(excinfo.value, (UnsafeQueryError, QueryTimeoutError))
    assert "nope" in str(excinfo.value)


# The data-modifying CTE passes layers 1 and 3, so only the role can stop it.
def test_data_modifying_cte_is_blocked_by_the_role():
    before = _orders_count()
    assert before > 0
    sql = "WITH x AS (DELETE FROM orders RETURNING *) SELECT count(*) FROM x"
    with pytest.raises(UnsafeQueryError) as excinfo:
        run_sql_safe(sql)
    assert type(excinfo.value.__cause__).__name__ == "InsufficientPrivilege"
    assert _orders_count() == before


# The timeout comes from the argument, not a fixed value: a 1 s query must pass with a 3 s limit.
def test_timeout_follows_the_argument():
    columns, rows = run_sql_safe("SELECT pg_sleep(1) AS slept", timeout_seconds=3)
    assert columns == ["slept"]
    assert len(rows) == 1


# The connection is closed even when the query fails. Failures are kept alive in a list so
# the interpreter cannot close the connections by garbage collection.
def test_connections_are_closed_after_errors():
    before = _open_readonly_connections()
    failures = []
    for _ in range(3):
        with pytest.raises(SqlExecutionError) as excinfo:
            run_sql_safe("SELECT nope FROM orders")
        failures.append(excinfo)
    assert _open_readonly_connections() == before


# SELECT ... INTO creates a table, and it passes layers 1 and 3, so only the role can stop it.
def test_select_into_is_blocked_by_the_role():
    with pytest.raises(UnsafeQueryError) as excinfo:
        run_sql_safe("SELECT * INTO ci_probe_copy FROM orders")
    assert type(excinfo.value.__cause__).__name__ == "InsufficientPrivilege"


# A temp table is allowed for the role, but the statement returns no rows, so it is reported as an error.
def test_a_statement_without_a_result_set_is_an_error_not_a_crash():
    with pytest.raises(SqlExecutionError, match="did not return any rows"):
        run_sql_safe("SELECT * INTO TEMP ci_probe_tmp FROM orders")

"""Giai đoạn 5 — thực thi SQL an toàn trên Postgres.

3 lớp phòng thủ độc lập (defense in depth) — xem PROGRESS.md Giai đoạn 5,
đặc biệt cảnh báo: psycopg2 KHÔNG tự chặn multi-statement như sqlite3.
"""


class SqlExecutionError(Exception):
    """Base exception cho tầng thực thi SQL."""


class UnsafeQueryError(SqlExecutionError):
    """SQL không phải SELECT đơn, hoặc chứa nhiều hơn 1 statement."""


class QueryTimeoutError(SqlExecutionError):
    """Query vượt quá statement_timeout."""


def _is_select_only(sql: str) -> bool:
    """TODO: lớp 1 — kiểm tra chuỗi (sau strip().lower()) bắt đầu bằng "select"."""
    raise NotImplementedError


def _is_single_statement(sql: str) -> bool:
    """TODO: lớp 3 — đếm statement thật bằng sqlparse.parse(sql), từ chối nếu >1."""
    raise NotImplementedError


def run_sql_safe(sql: str, max_rows: int = 100, timeout_seconds: float = 5.0):
    """TODO: lớp 1 (_is_select_only) -> lớp 2 (kết nối bằng role readonly_app,
    SET statement_timeout) -> lớp 3 (_is_single_statement) -> cursor.fetchmany(max_rows).
    Bắt psycopg2.errors.QueryCanceled -> raise QueryTimeoutError; các lỗi khác
    (SyntaxError, UndefinedColumn...) để nguyên hoặc bọc lại tuỳ thiết kế."""
    raise NotImplementedError

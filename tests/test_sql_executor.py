from app.sql_executor import _is_select_only, _is_single_statement


def test_select_statement_is_allowed():
    assert _is_select_only("SELECT 1") is True


def test_select_with_leading_whitespace_and_mixed_case_is_allowed():
    assert _is_select_only("  Select * from orders") is True


def test_delete_statement_is_rejected():
    assert _is_select_only("DELETE FROM orders") is False


def test_empty_string_is_rejected():
    assert _is_select_only("") is False


def test_single_select_statement_is_allowed():
    assert _is_single_statement("SELECT 1") is True


def test_single_select_statement_with_trailing_semicolon_is_allowed():
    assert _is_single_statement("SELECT 1;") is True


def test_stacked_query_is_rejected():
    assert _is_single_statement("SELECT 1; DROP TABLE orders;") is False


def test_double_semicolon_is_rejected():
    assert _is_single_statement("SELECT 1;;") is False

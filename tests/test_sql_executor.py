from app.sql_executor import _is_select_only, _is_single_statement


def test_select_statement_is_allowed():
    assert _is_select_only("SELECT 1") is True


def test_select_with_leading_whitespace_and_mixed_case_is_allowed():
    assert _is_select_only("  Select * from orders") is True


def test_delete_statement_is_rejected():
    assert _is_select_only("DELETE FROM orders") is False


def test_empty_string_is_rejected():
    assert _is_select_only("") is False


def test_cte_select_is_allowed():
    assert _is_select_only("WITH x AS (SELECT 1) SELECT * FROM x") is True


def test_data_modifying_cte_is_not_caught_by_this_layer_alone():
    """Documented gap: a CTE can hide a write inside a read-looking statement.
    No string-level check can reliably catch this — layer 2 (read-only DB
    role) is what actually blocks it. This test exists so the gap is visible
    and tracked, not silently missing from the test suite."""
    sql = "WITH x AS (DELETE FROM orders RETURNING *) SELECT * FROM x"
    assert _is_select_only(sql) is True


def test_explain_analyze_is_rejected():
    """EXPLAIN ANALYZE actually executes the statement it "analyzes" — if this
    prefix were ever accepted, EXPLAIN ANALYZE DELETE ... would really delete
    rows while looking like a harmless read. Must stay rejected."""
    assert _is_select_only("EXPLAIN ANALYZE DELETE FROM orders") is False


def test_call_statement_is_rejected():
    """CALL invokes a stored procedure, which can have arbitrary side effects."""
    assert _is_select_only("CALL some_procedure()") is False


def test_single_select_statement_is_allowed():
    assert _is_single_statement("SELECT 1") is True


def test_single_select_statement_with_trailing_semicolon_is_allowed():
    assert _is_single_statement("SELECT 1;") is True


def test_stacked_query_is_rejected():
    assert _is_single_statement("SELECT 1; DROP TABLE orders;") is False


def test_double_semicolon_is_rejected():
    assert _is_single_statement("SELECT 1;;") is False


def test_semicolon_inside_string_literal_is_not_miscounted():
    """This is the exact reason sqlparse was chosen over naive ';' counting —
    a semicolon inside quoted data must not be treated as a statement break."""
    assert _is_single_statement("SELECT * FROM orders WHERE note = 'hi; there'") is True

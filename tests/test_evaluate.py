from collections import Counter

from app.evaluate import normalize_result


def test_duplicate_rows_are_counted_not_collapsed():
    """The whole reason Counter is used instead of set — a predicted result
    missing one duplicate row must NOT be scored as matching."""
    assert normalize_result([(1,), (1,), (2,)]) == Counter({(1,): 2, (2,): 1})


def test_missing_duplicate_is_detected_as_different():
    full = normalize_result([(1,), (1,), (2,)])
    missing_one = normalize_result([(1,), (2,)])
    assert full != missing_one


def test_extra_columns_are_trimmed_when_expected_column_count_given():
    result = normalize_result([(1, "x", "extra")], expected_column_count=2)
    assert result == Counter({(1, "x"): 1})


def test_no_trimming_when_expected_column_count_not_given():
    result = normalize_result([(1, "x")])
    assert result == Counter({(1, "x"): 1})


def test_empty_rows_returns_empty_counter():
    assert normalize_result([]) == Counter()


def test_row_order_does_not_matter():
    assert normalize_result([(1,), (2,)]) == normalize_result([(2,), (1,)])

"""Measure execution accuracy by comparing query results, not SQL text."""

from collections import Counter


def normalize_result(rows, expected_column_count: int | None = None) -> Counter:
    """Normalize a result set (e.g. trim extra columns) before comparison."""
    if expected_column_count is not None:
        rows = [row[:expected_column_count] for row in rows]
    return Counter(rows)


def evaluate(use_self_correction: bool = False) -> None:
    """For each case in eval_test_set.EVAL_CASES, run predicted vs gold SQL, compare via
    Counter, and report. Catch errors per case instead of crashing."""
    raise NotImplementedError


if __name__ == "__main__":
    evaluate()

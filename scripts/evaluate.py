from collections import Counter

from sqlalchemy import create_engine

from schema_context import build_schema_context, DB_PATH
from llm_sql import generate_sql
from sql_executor import run_sql_safe
from eval_test_set import TEST_CASES


def normalize_result(columns, rows, expected_column_count=None):
    # Counter, not set: ignores row order (SQL doesn't guarantee it without
    # ORDER BY) but still tells apart e.g. 3 duplicate rows from 2 — set()
    # would silently treat those as equal.
    if expected_column_count is not None:
        # The question never specifies which columns to return, so a predicted
        # query that adds a supporting column (e.g. the COUNT it grouped by,
        # alongside the name being asked for) is not wrong — only compare the
        # leading `expected_column_count` values of each row. row[:n] is a
        # no-op when the row already has <= n columns, so this only ever
        # trims extras, never invents missing data for a genuinely short row.
        rows = [row[:expected_column_count] for row in rows]
    return Counter(rows)


def run_evaluation():
    engine = create_engine(f"sqlite:///{DB_PATH}")
    schema_context = build_schema_context(engine)

    correct = 0
    total = len(TEST_CASES)

    for case in TEST_CASES:
        question = case["question"]
        gold_sql = case["gold_sql"]

        predicted_sql = generate_sql(question, schema_context)

        gold_result = run_sql_safe(gold_sql)
        gold_normalized = normalize_result(*gold_result)
        gold_column_count = len(gold_result[0])

        # is_correct is (re)assigned in every branch below, every iteration —
        # never left over from a previous case (that was the earlier bug).
        predicted_result = None
        try:
            predicted_result = run_sql_safe(predicted_sql)
            predicted_normalized = normalize_result(*predicted_result, expected_column_count=gold_column_count)
            is_correct = predicted_normalized == gold_normalized
        except Exception as e:
            print(f"[{question}] execution error: {e}")
            is_correct = False

        status = "CORRECT" if is_correct else "WRONG"
        print(f"[{question}] {status}")
        print(f"  predicted_sql: {predicted_sql}")
        print(f"  gold_result:      {gold_result[1]}")
        print(f"  predicted_result: {predicted_result[1] if predicted_result else '(execution failed, see error above)'}")
        if is_correct:
            correct += 1

    print(f"\nAccuracy: {correct}/{total}")


if __name__ == "__main__":
    run_evaluation()

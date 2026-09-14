"""Evaluation set: (question, gold_sql) pairs. Never add these to the vector store."""

EVAL_CASES = [
    # TODO: at least 15 {"question": ..., "gold_sql": ...} pairs covering: simple counts,
    # JOIN+AVG, GROUP BY top-1, NULL traps, fan-out traps, HAVING via subquery,
    # multi-column sums, date filters, GROUP BY max, date comparisons, 3+ table joins,
    # and a few multi-row results.
]

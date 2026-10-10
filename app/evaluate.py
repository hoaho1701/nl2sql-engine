"""Measure execution accuracy by comparing query results, not SQL text."""

import argparse
import csv
import json
import os
import subprocess
from collections import Counter
from datetime import datetime

from dotenv import load_dotenv

from app.eval_test_set import EVAL_CASES, EVAL_VERSION
from app.llm_sql import generate_sql
from app.self_correct import answer_question
from app.sql_executor import SqlExecutionError, run_sql_safe
from app.vector_store import REPO_ROOT, nearest_example_similarity

# One gold query returns 2,997 rows, far above run_sql_safe's default cap of 100.
EVAL_MAX_ROWS = 100_000

# An eval question whose closest training example is at least this similar may have leaked.
LEAKAGE_THRESHOLD = 0.90

LOG_PATH = REPO_ROOT / "results" / "eval_log.csv"
RUNS_DIR = REPO_ROOT / "results" / "runs"   # one JSON file per run, named after the log row's timestamp
LOG_COLUMNS = [
    "timestamp",
    "config_description",
    "model",
    "use_self_correction",
    "n_cases",
    "n_correct",
    "accuracy",
    "n_exec_errors",
    "max_leak_similarity",
    "n_leak_over_threshold",
    "eval_version",
    "subset",
    "git_commit",
]

DEFAULT_SUBSETS = ("core", "dev")        # "heldout" is never part of the default
ALL_SUBSETS = ("core", "dev", "heldout")


def select_cases(subsets) -> list[dict]:
    """Return the cases in the given subsets; fail loudly on a typo, an empty result or a mix with heldout."""
    unknown = [s for s in subsets if s not in ALL_SUBSETS]
    if unknown:
        raise ValueError(f"unknown subset(s): {unknown}")
    if "heldout" in subsets and len(subsets) > 1:
        raise ValueError("run the heldout subset on its own")
    cases = [case for case in EVAL_CASES if case["subset"] in subsets]
    if not cases:
        raise ValueError("no eval case matches these subsets")
    return cases


def normalize_result(rows, expected_column_count: int | None = None) -> Counter:
    """Normalize a result set (e.g. trim extra columns) before comparison."""
    if expected_column_count is not None:
        rows = [row[:expected_column_count] for row in rows]
    return Counter(rows)


def evaluate(use_self_correction: bool = False, subsets=DEFAULT_SUBSETS) -> dict:
    """Run every case in EVAL_CASES and compare the predicted result with the gold result.

    Returns {"n_cases", "n_correct", "accuracy", "n_exec_errors", "results"}, where results
    has one dict per case: {"id", "kind", "subset", "question", "correct", "error", "sql", "attempts"}.

    Rules:
    - predicted SQL comes from generate_sql + run_sql_safe, or from answer_question when
      use_self_correction is True
    - run gold and predicted with max_rows=EVAL_MAX_ROWS
    - compare with normalize_result (trim predicted rows to the gold column count)
    - a SqlExecutionError from the predicted side is a wrong answer with the error recorded,
      not a crash; any other exception (including a gold query failing) propagates
    """
    results = []
    n_exec_errors = 0
    for case in select_cases(subsets):
        question = case["question"]
        gold_columns, gold_rows = run_sql_safe(case["gold_sql"], max_rows=EVAL_MAX_ROWS)
        sql = None
        error = None
        correct = False
        attempts = None
        try:
            if use_self_correction:
                answer = answer_question(question, max_rows=EVAL_MAX_ROWS)
                sql, columns, rows = answer.sql, answer.columns, answer.rows
                attempts = len(answer.attempts)
            else:
                sql = generate_sql(question)
                attempts = 1
                columns, rows = run_sql_safe(sql, max_rows=EVAL_MAX_ROWS)
            correct = normalize_result(rows, len(gold_columns)) == normalize_result(gold_rows)
        except SqlExecutionError as e:
            error = str(e)
            n_exec_errors += 1
        results.append({"id": case["id"], "kind": case["kind"], "subset": case["subset"],
                        "question": question, "correct": correct,
                        "error": error, "sql": sql, "attempts": attempts})
    n_correct = sum(r["correct"] for r in results)
    return {"n_cases": len(results), "n_correct": n_correct,
            "accuracy": n_correct/len(results) if len(results) else 0.0, "n_exec_errors": n_exec_errors, "results": results}


def _git_commit() -> str:
    """Short hash of HEAD, with "+dirty" if tracked code changed; "unknown" when git is unavailable.

    The log file itself is excluded, otherwise every run would make the next one look dirty.
    """
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", ".", ":(exclude)results/eval_log.csv"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return head + ("+dirty" if status else "")


def _append_log_row(row: dict) -> None:
    """Append one row to the experiment log, writing the header when the file is new.

    An existing file with a different header is refused: appending would silently shift columns.
    """
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not LOG_PATH.exists() or LOG_PATH.stat().st_size == 0
    if not write_header:
        with LOG_PATH.open(encoding="utf-8") as f:
            existing = f.readline().strip().split(",")
        if existing != LOG_COLUMNS:
            raise ValueError(f"{LOG_PATH} has columns {existing}, expected {LOG_COLUMNS}; migrate the file first")
    with LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def _write_run_file(row: dict, results: list[dict]) -> None:
    """Save the per-case results of one run next to the log; the file name is the row's timestamp."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = RUNS_DIR / (row["timestamp"].replace(":", "-") + ".json")
    with path.open("w", encoding="utf-8") as f:
        json.dump({"row": row, "results": results}, f, ensure_ascii=False, indent=2)


def run_and_log(use_self_correction: bool = False, config_description: str = "", subsets=DEFAULT_SUBSETS) -> dict:
    """Evaluate, measure possible leakage of training examples, and log the run."""
    load_dotenv(REPO_ROOT / ".env")
    summary = evaluate(use_self_correction, subsets)

    similarities = [nearest_example_similarity(case["question"]) for case in select_cases(subsets)]
    similarities = [value for value in similarities if value is not None]

    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "config_description": config_description,
        "model": os.environ["OLLAMA_SQL_MODEL"],
        "use_self_correction": use_self_correction,
        "n_cases": summary["n_cases"],
        "n_correct": summary["n_correct"],
        "accuracy": round(summary["accuracy"], 4),
        "n_exec_errors": summary["n_exec_errors"],
        "max_leak_similarity": round(max(similarities), 4) if similarities else "",
        "n_leak_over_threshold": sum(value >= LEAKAGE_THRESHOLD for value in similarities),
        "eval_version": EVAL_VERSION,
        "subset": "+".join(subsets),
        "git_commit": _git_commit(),
    }
    _append_log_row(row)
    _write_run_file(row, summary["results"])
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure execution accuracy on the eval set.")
    parser.add_argument("--self-correct", action="store_true", help="use the retry loop")
    parser.add_argument("--description", default="", help="one line describing this run")
    parser.add_argument("--subsets", nargs="+", choices=ALL_SUBSETS, default=list(DEFAULT_SUBSETS))
    args = parser.parse_args()
    row = run_and_log(args.self_correct, args.description, args.subsets)
    print(
        f"{row['n_correct']}/{row['n_cases']} correct (accuracy {row['accuracy']}), "
        f"{row['n_exec_errors']} execution errors, "
        f"{row['n_leak_over_threshold']} possible leaks (max similarity {row['max_leak_similarity']})"
    )


if __name__ == "__main__":
    main()

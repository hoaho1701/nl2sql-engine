"""Checks on the training examples: shape, no overlap with the eval set, and that they run."""

import re

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.eval_test_set import EVAL_CASES
from app.load_data import get_engine
from app.sql_executor import _is_select_only
from app.training_examples import TRAINING_EXAMPLES

MIN_EXAMPLES = 15


def _normalize(value: str) -> str:
    """Lowercase, collapse whitespace and drop a trailing semicolon, for overlap checks."""
    return re.sub(r"\s+", " ", value).strip().rstrip(";").strip().lower()


def _database_is_up() -> bool:
    try:
        with get_engine().connect():
            return True
    except OperationalError:
        return False


def test_there_are_enough_examples():
    assert len(TRAINING_EXAMPLES) >= MIN_EXAMPLES


def test_every_example_has_a_question_and_a_sql_string():
    for example in TRAINING_EXAMPLES:
        assert set(example) == {"question", "sql"}
        assert example["question"].strip()
        assert example["sql"].strip()


def test_questions_are_unique():
    questions = [_normalize(example["question"]) for example in TRAINING_EXAMPLES]
    assert len(set(questions)) == len(questions)


def test_sql_statements_are_unique():
    statements = [_normalize(example["sql"]) for example in TRAINING_EXAMPLES]
    assert len(set(statements)) == len(statements)


def test_no_training_question_appears_in_the_eval_set():
    eval_questions = {_normalize(case["question"]) for case in EVAL_CASES}
    for example in TRAINING_EXAMPLES:
        assert _normalize(example["question"]) not in eval_questions, example["question"]


def test_no_training_sql_appears_in_the_eval_set():
    eval_statements = {_normalize(case["gold_sql"]) for case in EVAL_CASES}
    for example in TRAINING_EXAMPLES:
        assert _normalize(example["sql"]) not in eval_statements, example["question"]


@pytest.mark.parametrize("example", TRAINING_EXAMPLES, ids=lambda e: e["question"][:50])
def test_every_example_is_a_single_select(example):
    assert _is_select_only(example["sql"])


@pytest.mark.skipif(not _database_is_up(), reason="Postgres is not running")
@pytest.mark.parametrize("example", TRAINING_EXAMPLES, ids=lambda e: e["question"][:50])
def test_every_example_runs_against_postgres(example):
    with get_engine().connect() as connection:
        connection.execute(text(example["sql"])).fetchall()


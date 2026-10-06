"""Tests for self_correct.answer_question: SQL generation and execution are replaced by fakes."""

import logging
from types import SimpleNamespace

import pytest

from app import self_correct
from app.sql_executor import QueryTimeoutError, SqlExecutionError, UnsafeQueryError

OK = (["n"], [(1,)])


@pytest.fixture
def pipeline(monkeypatch):
    """Fake generate_sql and run_sql_safe that record every call.

    sqls: queued answers from the model; once used up, every call returns a new unique SQL.
    outcomes: queued results of execution (an exception instance is raised, a tuple is
    returned); once used up, the last one repeats.
    """
    fake = SimpleNamespace(sqls=[], outcomes=[OK], generate_calls=[], run_calls=[])

    def fake_generate(question, feedback=None):
        fake.generate_calls.append({"question": question, "feedback": feedback})
        n = len(fake.generate_calls)
        return fake.sqls[n - 1] if n <= len(fake.sqls) else f"SELECT {n}"

    def fake_run(sql, *args, **kwargs):
        fake.run_calls.append(sql)
        n = len(fake.run_calls)
        outcome = fake.outcomes[min(n, len(fake.outcomes)) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    # Patch the names where self_correct looks them up, not where they are defined.
    monkeypatch.setattr(self_correct, "generate_sql", fake_generate)
    monkeypatch.setattr(self_correct, "run_sql_safe", fake_run)
    return fake


# The happy path.
def test_success_on_the_first_try_does_not_retry(pipeline):
    pipeline.sqls = ["SELECT count(*) AS n FROM orders"]

    result = self_correct.answer_question("How many orders?")

    assert result.sql == "SELECT count(*) AS n FROM orders"
    assert result.columns == ["n"]
    assert result.rows == [(1,)]
    assert len(pipeline.generate_calls) == 1
    assert pipeline.generate_calls[0]["question"] == "How many orders?"
    assert not pipeline.generate_calls[0]["feedback"]
    assert len(pipeline.run_calls) == 1
    assert len(result.attempts) == 1
    assert result.attempts[0].error is None


# A plain SQL error is retried and the second attempt wins.
def test_sql_error_is_retried_and_the_second_attempt_is_returned(pipeline):
    pipeline.sqls = ["SELECT nope FROM orders", "SELECT count(*) AS n FROM orders"]
    pipeline.outcomes = [SqlExecutionError('column "nope" does not exist'), OK]

    result = self_correct.answer_question("How many orders?")

    assert result.sql == "SELECT count(*) AS n FROM orders"
    assert len(result.attempts) == 2
    assert result.attempts[0].sql == "SELECT nope FROM orders"
    assert 'column "nope" does not exist' in result.attempts[0].error
    assert result.attempts[1].error is None


# What the model is told on the retry.
def test_retry_sends_the_bad_sql_and_the_postgres_message_back(pipeline):
    pipeline.sqls = ["SELECT nope FROM orders", "SELECT 1"]
    pipeline.outcomes = [SqlExecutionError('column "nope" does not exist'), OK]

    self_correct.answer_question("How many orders?")

    first, second = pipeline.generate_calls
    assert not first["feedback"]
    assert {"role": "assistant", "content": "SELECT nope FROM orders"} in second["feedback"]
    last = second["feedback"][-1]
    assert last["role"] == "user"
    assert 'column "nope" does not exist' in last["content"]


def test_retry_keeps_the_original_question(pipeline):
    pipeline.outcomes = [SqlExecutionError("boom"), OK]

    self_correct.answer_question("How many orders?")

    assert [c["question"] for c in pipeline.generate_calls] == ["How many orders?"] * 2


# The retry budget.
def test_gives_up_after_max_retries_and_raises_the_last_error(pipeline):
    pipeline.outcomes = [
        SqlExecutionError("e1"),
        SqlExecutionError("e2"),
        SqlExecutionError("e3"),
    ]

    with pytest.raises(SqlExecutionError) as excinfo:
        self_correct.answer_question("How many orders?", max_retries=2)

    assert len(pipeline.generate_calls) == 3
    assert str(excinfo.value) == "e3"


def test_max_retries_zero_means_a_single_attempt(pipeline):
    pipeline.outcomes = [SqlExecutionError("boom")]

    with pytest.raises(SqlExecutionError):
        self_correct.answer_question("How many orders?", max_retries=0)

    assert len(pipeline.generate_calls) == 1


def test_stops_when_the_model_repeats_the_failed_sql(pipeline):
    pipeline.sqls = ["SELECT bad", "SELECT bad"]
    pipeline.outcomes = [SqlExecutionError("boom")]

    with pytest.raises(SqlExecutionError) as excinfo:
        self_correct.answer_question("How many orders?", max_retries=5)

    assert len(pipeline.generate_calls) == 2
    assert len(pipeline.run_calls) == 1
    assert str(excinfo.value) == "boom"


def test_a_repeat_that_differs_only_in_whitespace_still_counts_as_a_repeat(pipeline):
    pipeline.sqls = ["SELECT bad", "  SELECT bad\n"]
    pipeline.outcomes = [SqlExecutionError("boom")]

    with pytest.raises(SqlExecutionError):
        self_correct.answer_question("How many orders?", max_retries=5)

    assert len(pipeline.run_calls) == 1


def test_negative_max_retries_is_rejected_before_anything_runs(pipeline):
    with pytest.raises(ValueError):
        self_correct.answer_question("How many orders?", max_retries=-1)

    assert pipeline.generate_calls == []


# Timeouts and rejected queries get at most one retry, however large max_retries is.
def test_timeout_is_retried_at_most_once(pipeline):
    pipeline.outcomes = [QueryTimeoutError("slow")]

    with pytest.raises(QueryTimeoutError):
        self_correct.answer_question("How many orders?", max_retries=5)

    assert len(pipeline.generate_calls) == 2


def test_rejected_query_is_retried_at_most_once(pipeline):
    pipeline.outcomes = [UnsafeQueryError("Only SELECT or WITH queries are allowed.")]

    with pytest.raises(UnsafeQueryError):
        self_correct.answer_question("How many orders?", max_retries=5)

    assert len(pipeline.generate_calls) == 2


def test_each_kind_of_error_uses_its_own_allowance_within_the_total_budget(pipeline):
    pipeline.outcomes = [QueryTimeoutError("slow"), SqlExecutionError("boom"), OK]

    result = self_correct.answer_question("How many orders?", max_retries=2)

    assert len(result.attempts) == 3
    assert result.attempts[-1].error is None


def test_total_budget_is_shared_across_kinds_of_error(pipeline):
    pipeline.outcomes = [QueryTimeoutError("slow"), SqlExecutionError("boom")]

    with pytest.raises(SqlExecutionError):
        self_correct.answer_question("How many orders?", max_retries=1)

    assert len(pipeline.generate_calls) == 2


# The wording of the retry depends on what went wrong.
def test_timeout_retry_tells_the_model_the_query_was_too_slow(pipeline):
    pipeline.sqls = ["SELECT slow", "SELECT 1"]
    pipeline.outcomes = [QueryTimeoutError("Query exceeded the 5.0 s time limit."), OK]

    self_correct.answer_question("How many orders?")

    feedback = pipeline.generate_calls[1]["feedback"]
    assert {"role": "assistant", "content": "SELECT slow"} in feedback
    assert "time" in feedback[-1]["content"].lower()


def test_rejected_query_retry_includes_the_rejection_reason(pipeline):
    pipeline.outcomes = [UnsafeQueryError("Only a single SQL statement is allowed."), OK]

    self_correct.answer_question("How many orders?")

    feedback = pipeline.generate_calls[1]["feedback"]
    assert "Only a single SQL statement is allowed." in feedback[-1]["content"]


# Failures that are not SQL problems must not be retried.
def test_non_sql_errors_from_execution_are_not_retried(pipeline):
    pipeline.outcomes = [RuntimeError("database is down")]

    with pytest.raises(RuntimeError):
        self_correct.answer_question("How many orders?")

    assert len(pipeline.generate_calls) == 1


def test_errors_from_the_model_call_propagate_and_nothing_is_executed(pipeline, monkeypatch):
    def broken_generate(question, feedback=None):
        raise ConnectionError("ollama is down")

    monkeypatch.setattr(self_correct, "generate_sql", broken_generate)

    with pytest.raises(ConnectionError):
        self_correct.answer_question("How many orders?")

    assert pipeline.run_calls == []


# Every attempt is logged.
def test_every_attempt_is_logged(pipeline, caplog):
    pipeline.outcomes = [SqlExecutionError("boom"), OK]
    caplog.set_level(logging.INFO, logger="app.self_correct")

    self_correct.answer_question("How many orders?")

    records = [r for r in caplog.records if r.name == "app.self_correct"]
    assert len(records) == 2
    assert "boom" in records[0].getMessage()
    assert "boom" not in records[1].getMessage()
    # Every placeholder must have been filled in, with the attempt number.
    assert "%" not in records[0].getMessage()
    assert "%" not in records[1].getMessage()
    assert "2" in records[1].getMessage()
    assert records[0].levelno == logging.WARNING
    assert records[1].levelno == logging.INFO

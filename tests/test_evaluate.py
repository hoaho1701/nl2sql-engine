"""Tests for evaluate: result comparison, the evaluation loop (with fakes) and the run log."""

import csv
from collections import Counter
from types import SimpleNamespace

import pytest

from app import evaluate as ev
from app.evaluate import normalize_result
from app.sql_executor import SqlExecutionError


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


# --------------------------------------------------------------------------
# evaluate(): the model, the executor and answer_question are replaced by fakes
# --------------------------------------------------------------------------

ONE = (["n"], [(1,)])
TWO = (["n"], [(2,)])


@pytest.fixture
def world(monkeypatch):
    """Fake eval set, model and executor.

    cases: eval cases to run. predicted: question -> SQL the "model" writes.
    outcomes: SQL -> (columns, rows), or an exception instance to raise when it runs.
    answer_attempts: question -> number of attempts the fake answer_question reports.
    """
    world = SimpleNamespace(
        cases=[],
        predicted={},
        outcomes={},
        answer_attempts={},
        generate_calls=[],
        answer_calls=[],
        run_calls=[],
    )

    def fake_generate(question, feedback=None):
        world.generate_calls.append(question)
        return world.predicted[question]

    def fake_run(sql, *args, **kwargs):
        world.run_calls.append({"sql": sql, "kwargs": kwargs})
        outcome = world.outcomes[sql]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def fake_answer(question, max_retries=2, max_rows=100):
        world.answer_calls.append({"question": question, "max_rows": max_rows})
        sql = world.predicted[question]
        columns, rows = fake_run(sql, max_rows=max_rows)
        attempts = [None] * world.answer_attempts.get(question, 1)
        return SimpleNamespace(sql=sql, columns=columns, rows=rows, attempts=attempts)

    monkeypatch.setattr(ev, "EVAL_CASES", world.cases)
    monkeypatch.setattr(ev, "generate_sql", fake_generate)
    monkeypatch.setattr(ev, "run_sql_safe", fake_run)
    monkeypatch.setattr(ev, "answer_question", fake_answer)
    return world


def add_case(world, n, gold=ONE, predicted=ONE, subset="core"):
    """Add case n: question "Qn", gold SQL "GOLDn", predicted SQL "PREDn"."""
    question, gold_sql, predicted_sql = f"Q{n}", f"GOLD{n}", f"PRED{n}"
    world.cases.append({"question": question, "gold_sql": gold_sql, "subset": subset})
    world.predicted[question] = predicted_sql
    world.outcomes[gold_sql] = gold
    world.outcomes[predicted_sql] = predicted


def test_all_correct_gives_accuracy_one(world):
    add_case(world, 1)
    add_case(world, 2)

    summary = ev.evaluate()

    assert summary["n_cases"] == 2
    assert summary["n_correct"] == 2
    assert summary["accuracy"] == 1.0
    assert summary["n_exec_errors"] == 0


def test_a_wrong_result_is_not_correct(world):
    add_case(world, 1)
    add_case(world, 2, predicted=TWO)

    summary = ev.evaluate()

    assert [r["correct"] for r in summary["results"]] == [True, False]
    assert summary["results"][1]["error"] is None
    assert summary["n_correct"] == 1
    assert summary["accuracy"] == 0.5


def test_row_order_does_not_change_the_verdict(world):
    add_case(world, 1, gold=(["n"], [(1,), (2,)]), predicted=(["n"], [(2,), (1,)]))

    assert ev.evaluate()["results"][0]["correct"] is True


def test_a_missing_duplicate_row_is_wrong(world):
    add_case(world, 1, gold=(["n"], [(1,), (1,), (2,)]), predicted=(["n"], [(1,), (2,)]))

    assert ev.evaluate()["results"][0]["correct"] is False


def test_extra_predicted_columns_are_trimmed_to_the_gold_width(world):
    add_case(world, 1, gold=ONE, predicted=(["n", "extra"], [(1, "x")]))

    assert ev.evaluate()["results"][0]["correct"] is True


def test_fewer_predicted_columns_than_gold_is_wrong(world):
    add_case(world, 1, gold=(["a", "b"], [(1, 2)]), predicted=(["a"], [(1,)]))

    assert ev.evaluate()["results"][0]["correct"] is False


def test_a_predicted_execution_error_is_a_wrong_answer_not_a_crash(world):
    add_case(world, 1, predicted=SqlExecutionError("boom"))

    summary = ev.evaluate()

    result = summary["results"][0]
    assert result["correct"] is False
    assert result["error"] == "boom"
    assert summary["n_exec_errors"] == 1
    assert summary["n_correct"] == 0


def test_an_error_in_the_first_case_does_not_leak_into_the_next(world):
    add_case(world, 1, predicted=SqlExecutionError("boom"))
    add_case(world, 2)

    first, second = ev.evaluate()["results"]

    assert first["correct"] is False and first["error"] == "boom"
    assert second["correct"] is True and second["error"] is None


def test_a_wrong_case_does_not_make_the_next_case_wrong(world):
    add_case(world, 1, predicted=TWO)
    add_case(world, 2)
    add_case(world, 3, predicted=TWO)

    assert [r["correct"] for r in ev.evaluate()["results"]] == [False, True, False]


def test_a_failing_gold_query_is_not_swallowed(world):
    add_case(world, 1, gold=SqlExecutionError("gold is broken"))

    with pytest.raises(SqlExecutionError):
        ev.evaluate()


def test_infrastructure_errors_stop_the_run(world, monkeypatch):
    add_case(world, 1)

    def broken_generate(question, feedback=None):
        raise ConnectionError("ollama is down")

    monkeypatch.setattr(ev, "generate_sql", broken_generate)

    with pytest.raises(ConnectionError):
        ev.evaluate()


def test_an_empty_eval_set_is_refused(world):
    with pytest.raises(ValueError):
        ev.evaluate()


def test_evaluate_runs_only_the_default_subsets(world):
    add_case(world, 1, subset="core")
    add_case(world, 2, subset="dev")
    add_case(world, 3, subset="heldout")

    summary = ev.evaluate()

    assert [r["question"] for r in summary["results"]] == ["Q1", "Q2"]


def test_evaluate_can_run_the_heldout_subset_alone(world):
    add_case(world, 1, subset="core")
    add_case(world, 2, subset="heldout")

    summary = ev.evaluate(subsets=("heldout",))

    assert [r["question"] for r in summary["results"]] == ["Q2"]


def test_select_cases_rejects_an_unknown_subset(world):
    add_case(world, 1)
    with pytest.raises(ValueError):
        ev.select_cases(("core", "typo"))


def test_select_cases_refuses_heldout_mixed_with_other_subsets(world):
    add_case(world, 1, subset="core")
    add_case(world, 2, subset="heldout")
    with pytest.raises(ValueError):
        ev.select_cases(("core", "heldout"))


def test_select_cases_fails_when_nothing_matches(world):
    add_case(world, 1, subset="core")
    with pytest.raises(ValueError):
        ev.select_cases(("dev",))


def test_without_self_correction_the_model_is_called_directly(world):
    add_case(world, 1)
    add_case(world, 2)

    ev.evaluate(use_self_correction=False)

    assert world.generate_calls == ["Q1", "Q2"]
    assert world.answer_calls == []


def test_with_self_correction_answer_question_is_used(world):
    add_case(world, 1)
    add_case(world, 2)

    ev.evaluate(use_self_correction=True)

    assert [c["question"] for c in world.answer_calls] == ["Q1", "Q2"]
    assert world.generate_calls == []


def test_gold_and_predicted_queries_are_not_cut_at_the_default_row_cap(world):
    add_case(world, 1)

    ev.evaluate()

    assert len(world.run_calls) == 2
    assert all(call["kwargs"]["max_rows"] >= 3000 for call in world.run_calls)


def test_self_correction_also_uses_the_large_row_cap(world):
    add_case(world, 1)

    ev.evaluate(use_self_correction=True)

    assert world.answer_calls[0]["max_rows"] >= 3000
    assert world.run_calls[0]["kwargs"]["max_rows"] >= 3000


def test_results_record_question_sql_and_attempts(world):
    add_case(world, 1)

    result = ev.evaluate()["results"][0]

    assert result["question"] == "Q1"
    assert result["sql"] == "PRED1"
    assert result["attempts"] == 1


def test_results_count_the_attempts_reported_by_answer_question(world):
    add_case(world, 1)
    world.answer_attempts["Q1"] = 3

    result = ev.evaluate(use_self_correction=True)["results"][0]

    assert result["attempts"] == 3


def test_a_self_correction_failure_is_recorded_as_a_wrong_answer(world, monkeypatch):
    add_case(world, 1)

    def giving_up(question, max_retries=2, max_rows=100):
        raise SqlExecutionError("could not fix it")

    monkeypatch.setattr(ev, "answer_question", giving_up)

    result = ev.evaluate(use_self_correction=True)["results"][0]

    assert result["correct"] is False
    assert result["error"] == "could not fix it"
    assert result["sql"] is None


# --------------------------------------------------------------------------
# run_and_log(): the experiment log
# --------------------------------------------------------------------------


@pytest.fixture
def logged(monkeypatch, tmp_path):
    """run_and_log with a fake evaluate, fake similarities and a log file in a temp folder."""
    log = SimpleNamespace(
        path=tmp_path / "results" / "eval_log.csv",
        summary={"n_cases": 4, "n_correct": 3, "accuracy": 0.75, "n_exec_errors": 1, "results": []},
        similarities={},
    )
    monkeypatch.setenv("OLLAMA_SQL_MODEL", "test-model")
    monkeypatch.setattr(ev, "LOG_PATH", log.path)
    monkeypatch.setattr(ev, "EVAL_CASES", [{"question": f"Q{i}", "gold_sql": "", "subset": "core"} for i in range(4)])
    monkeypatch.setattr(ev, "evaluate", lambda use_self_correction=False, subsets=ev.DEFAULT_SUBSETS: log.summary)
    monkeypatch.setattr(ev, "_git_commit", lambda: "abc1234")
    monkeypatch.setattr(ev, "nearest_example_similarity", lambda q: log.similarities.get(q, 0.5))
    return log


def read_log(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_run_and_log_creates_the_folder_and_writes_a_header(logged):
    ev.run_and_log(False, "baseline")

    with logged.path.open(encoding="utf-8") as f:
        assert f.readline().strip().split(",") == ev.LOG_COLUMNS


def test_run_and_log_records_the_run(logged):
    ev.run_and_log(True, "with retries")

    row = read_log(logged.path)[0]
    assert row["config_description"] == "with retries"
    assert row["model"] == "test-model"
    assert row["use_self_correction"] == "True"
    assert (row["n_cases"], row["n_correct"], row["n_exec_errors"]) == ("4", "3", "1")
    assert float(row["accuracy"]) == 0.75
    assert row["timestamp"]


def test_each_run_appends_one_row_and_the_header_is_written_once(logged):
    ev.run_and_log(False, "first")
    ev.run_and_log(True, "second")

    rows = read_log(logged.path)
    assert [r["config_description"] for r in rows] == ["first", "second"]
    assert logged.path.read_text(encoding="utf-8").count("timestamp") == 1


def test_run_and_log_records_the_leakage_measurement(logged):
    logged.similarities = {"Q0": 0.95, "Q1": 0.90, "Q2": 0.80, "Q3": 0.3}

    ev.run_and_log()

    row = read_log(logged.path)[0]
    assert float(row["max_leak_similarity"]) == 0.95
    assert row["n_leak_over_threshold"] == "2"


def test_questions_without_a_similarity_are_ignored_in_the_leakage_measurement(logged, monkeypatch):
    monkeypatch.setattr(ev, "nearest_example_similarity", lambda q: None)

    ev.run_and_log()

    row = read_log(logged.path)[0]
    assert row["max_leak_similarity"] == ""
    assert row["n_leak_over_threshold"] == "0"


def test_run_and_log_records_version_subset_and_commit(logged):
    ev.run_and_log(subsets=("core", "dev"))

    row = read_log(logged.path)[0]
    assert row["eval_version"] == str(ev.EVAL_VERSION)
    assert row["subset"] == "core+dev"
    assert row["git_commit"] == "abc1234"


def test_a_log_with_an_old_header_is_refused(logged):
    logged.path.parent.mkdir(parents=True)
    logged.path.write_text("timestamp,model\n", encoding="utf-8")

    with pytest.raises(ValueError):
        ev.run_and_log()

    assert logged.path.read_text(encoding="utf-8") == "timestamp,model\n"


def _fake_git(monkeypatch, head="abc1234", status=""):
    def fake_run(cmd, **kwargs):
        out = head if "rev-parse" in cmd else status
        return SimpleNamespace(stdout=out + "\n")
    monkeypatch.setattr(ev.subprocess, "run", fake_run)


def test_git_commit_is_the_short_hash_when_the_tree_is_clean(monkeypatch):
    _fake_git(monkeypatch)
    assert ev._git_commit() == "abc1234"


def test_git_commit_is_marked_dirty_when_files_changed(monkeypatch):
    _fake_git(monkeypatch, status=" M app/evaluate.py")
    assert ev._git_commit() == "abc1234+dirty"


def test_git_commit_is_unknown_when_git_fails(monkeypatch):
    def boom(cmd, **kwargs):
        raise FileNotFoundError("git")
    monkeypatch.setattr(ev.subprocess, "run", boom)
    assert ev._git_commit() == "unknown"

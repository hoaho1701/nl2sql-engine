"""Tests for llm_sql.generate_sql: retrieval and the model call are replaced by fakes."""

from types import SimpleNamespace

import pytest

from app import llm_sql


class FakeCompletions:
    """Stand-in for client.chat.completions: records every call and returns a canned answer."""

    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        message = SimpleNamespace(content=self.answer)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@pytest.fixture
def model(monkeypatch):
    """Fake Ollama client plus a fake retrieve; returns an object holding both recorders."""
    completions = FakeCompletions(answer="SELECT 1")
    retrieved_for = []

    def fake_retrieve(question, *args, **kwargs):
        retrieved_for.append(question)
        return "CONTEXT-FROM-RETRIEVE"

    monkeypatch.setenv("OLLAMA_SQL_MODEL", "test-model")
    # Patch the names where llm_sql looks them up, not where they are defined.
    monkeypatch.setattr(llm_sql, "_get_client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=completions)))
    monkeypatch.setattr(llm_sql, "retrieve", fake_retrieve)
    return SimpleNamespace(completions=completions, retrieved_for=retrieved_for)


def test_generate_sql_returns_the_model_answer_unchanged(model):
    # Cleaning (fences, whitespace, the trailing semicolon) is left to the execution layer.
    model.completions.answer = "  SELECT COUNT(*) FROM orders;\n"

    assert llm_sql.generate_sql("How many orders?") == "  SELECT COUNT(*) FROM orders;\n"


def test_generate_sql_retrieves_context_for_the_question(model):
    llm_sql.generate_sql("How many orders?")

    assert model.retrieved_for == ["How many orders?"]


def test_generate_sql_sends_the_context_in_the_system_message(model):
    llm_sql.generate_sql("How many orders?")

    messages = model.completions.calls[0]["messages"]
    assert messages[0]["role"] == "system"
    assert "CONTEXT-FROM-RETRIEVE" in messages[0]["content"]


def test_generate_sql_sends_the_question_as_the_last_user_message(model):
    llm_sql.generate_sql("How many orders?")

    messages = model.completions.calls[0]["messages"]
    assert messages[-1] == {"role": "user", "content": "How many orders?"}


def test_generate_sql_uses_temperature_zero(model):
    llm_sql.generate_sql("How many orders?")

    assert model.completions.calls[0]["temperature"] == 0


def test_generate_sql_uses_the_model_named_in_the_environment(model):
    llm_sql.generate_sql("How many orders?")

    assert model.completions.calls[0]["model"] == "test-model"


def test_generate_sql_calls_the_model_exactly_once(model):
    llm_sql.generate_sql("How many orders?")

    assert len(model.completions.calls) == 1
    assert len(model.retrieved_for) == 1

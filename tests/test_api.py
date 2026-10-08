"""Tests for api's Pydantic models and CORS config (no live server needed)."""

import pytest
import httpx
import openai
import psycopg2
import logging

from types import SimpleNamespace
from decimal import Decimal
from datetime import datetime

from fastapi.testclient import TestClient

from app import api
from app.api import QueryRequest, QueryResponse, app
from app.sql_executor import UnsafeQueryError, QueryTimeoutError, SqlExecutionError

client = TestClient(app)


def test_query_request_accepts_a_question_string():
    req = QueryRequest(question="How many orders?")
    assert req.question == "How many orders?"


def test_query_response_explanation_defaults_to_none():
    resp = QueryResponse(sql="SELECT 1", columns=["n"], rows=[(1,)], attempts=1)
    assert resp.explanation is None


def test_cors_headers_present_for_allowed_frontend_origin():
    response = client.options(
        "/",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


@pytest.fixture
def ask(monkeypatch):
    """Fake answer_question; returns an object with the client, the recorded calls and the state."""
    calls = []
    state = SimpleNamespace(result=SimpleNamespace(sql="SELECT 1", columns=["n"], rows=[(1,)], attempts=[1]), error=None)

    def fake(question):
        calls.append(question)
        if state.error:
            raise state.error
        return state.result

    monkeypatch.setattr(api, "answer_question", fake)
    api_client = TestClient(app, raise_server_exceptions=False)
    return SimpleNamespace(client=api_client, calls=calls, state=state)


def test_a_successful_query_returns_the_four_fields(ask):
    response = ask.client.post("/query", json={"question": "How many orders?"})

    assert response.status_code == 200
    assert response.json() == {
        "sql": "SELECT 1",
        "columns": ["n"],
        "rows": [[1]],
        "attempts": 1,
        "explanation": None,
    }


def test_the_question_is_stripped_before_it_reached_the_model(ask):
    ask.client.post("/query", json={"question": "  How many orders?  "})
    assert ask.calls == ["How many orders?"]


def test_decimals_and_dates_are_sent_as_string(ask):
    ask.state.result.rows = [(Decimal("2.50"), datetime(2018, 1, 1))]
    response = ask.client.post("/query", json={"question": "x"})
    assert response.json()["rows"] == [["2.50", "2018-01-01T00:00:00"]]


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (UnsafeQueryError("..."), 400),
        (QueryTimeoutError("..."), 504),
        (SqlExecutionError("..."), 422),
        (psycopg2.OperationalError("..."), 503),
        (openai.APIConnectionError(request=httpx.Request("POST", "http://localhost:11434")), 503),
        (RuntimeError("..."), 500),
    ],
)
def test_errors_map_to_the_agreed_status_code(ask, error, status):
    ask.state.error = error
    response = ask.client.post("/query", json={"question": "x"})
    assert response.status_code == status


@pytest.mark.parametrize(
    "error",
    [
        UnsafeQueryError("secret"),
        QueryTimeoutError("secret"),
        SqlExecutionError("secret"),
        psycopg2.OperationalError("secret"),
    ],
)
def test_error_details_are_not_leaked(ask, error):
    ask.state.error = error
    response = ask.client.post("/query", json={"question": "x"})
    assert "secret" not in response.text


@pytest.mark.parametrize(
    "error",
    [
        UnsafeQueryError("unsafe detail"),
        QueryTimeoutError("timeout detail"),
        SqlExecutionError("sql detail"),
    ],
)
def test_each_expected_error_is_logged(ask, caplog, error):
    ask.state.error = error
    with caplog.at_level(logging.WARNING, logger="app.api"):
        ask.client.post("/query", json={"question": "x"})
    assert str(error) in caplog.text


@pytest.mark.parametrize("body", [{"question": ""}, {"question": "   "}, {}])
def test_a_bad_question_is_rejected_before_the_model_is_called(ask, body):
    response = ask.client.post("/query", json=body)

    assert response.status_code == 422
    assert ask.calls == []
    assert isinstance(response.json()["detail"], list)


def test_infrastructure_failure_is_logged_with_a_traceback(ask, caplog):
    ask.state.error = psycopg2.OperationalError("____")
    with caplog.at_level(logging.ERROR, logger="app.api"):
        ask.client.post("/query", json={"question": "x"})
    assert any(record.exc_info for record in caplog.records)

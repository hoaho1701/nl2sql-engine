from fastapi.testclient import TestClient

from app.api import QueryRequest, QueryResponse, app

client = TestClient(app)


def test_query_request_accepts_a_question_string():
    req = QueryRequest(question="How many orders?")
    assert req.question == "How many orders?"


def test_query_response_explanation_defaults_to_none():
    resp = QueryResponse(sql="SELECT 1", rows=[(1,)])
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

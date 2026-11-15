from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_ticket_service
from app.main import app


def test_health_and_readiness(client: TestClient) -> None:
    assert client.get("/health").status_code == 200
    readiness = client.get("/readiness")
    assert readiness.status_code == 200
    assert readiness.json()["status"] == "ready"
    assert readiness.json()["database"] is True
    assert readiness.json()["llm_mode"] == "deterministic_fallback"


def test_readiness_reports_database_outage(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    check_database = Mock(return_value=False)
    monkeypatch.setattr("app.main.check_database", check_database)

    readiness = client.get("/readiness")

    assert readiness.status_code == 503
    assert readiness.json()["status"] == "not_ready"
    assert readiness.json()["database"] is False
    check_database.assert_called_once_with()
    assert client.get("/health").status_code == 200


def test_unhandled_error_hides_details_and_preserves_request_id(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail() -> None:
        raise RuntimeError("private backend diagnostic")

    monkeypatch.setitem(app.dependency_overrides, get_ticket_service, fail)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/tickets", headers={"X-Request-ID": "test-request"})

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "test-request"
    assert response.json() == {
        "error": "internal_server_error",
        "detail": "An unexpected error occurred.",
        "request_id": "test-request",
    }


def test_create_list_filter_and_get_ticket(client: TestClient) -> None:
    ticket = _create_ticket(client, "Payment failed", "My payment failed during checkout and I need help.")

    list_response = client.get("/tickets?search=payment&limit=10")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == ticket["id"]

    get_response = client.get(f"/tickets/{ticket['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["subject"] == "Payment failed"


def test_workflow_run_persists_steps_and_rag_context(client: TestClient) -> None:
    ticket = _create_ticket(
        client,
        "Production API returns 500",
        "Our production API endpoint returns 500 errors and customers are blocked.",
    )

    response = client.post(f"/tickets/{ticket['id']}/workflow-runs")
    assert response.status_code == 200
    workflow = response.json()["workflow"]
    assert workflow["run_id"]
    assert workflow["classification"]["category"] == "api_error"
    assert workflow["classification"]["priority"] == "urgent"
    assert workflow["retrieved_context"]
    assert workflow["escalation_required"] is True
    assert workflow["quality_score"] >= 0.75
    assert workflow["workflow_steps"] == [
        "intake_validator",
        "classifier",
        "rag_retriever",
        "resolution_planner",
        "response_writer",
        "escalation_decider",
        "quality_guardrail",
        "audit_logger",
    ]

    runs = client.get(f"/tickets/{ticket['id']}/workflow-runs")
    assert runs.status_code == 200
    assert len(runs.json()) == 1
    assert len(runs.json()[0]["steps"]) == 8

    run = client.get(f"/workflow-runs/{workflow['run_id']}")
    assert run.status_code == 200
    assert run.json()["trace_id"] == workflow["trace_id"]


def test_knowledge_reindex_requires_api_key_and_search_works(client: TestClient) -> None:
    unauthorized = client.post("/knowledge/reindex")
    assert unauthorized.status_code == 401

    reindex = client.post("/knowledge/reindex", headers={"X-API-Key": "dev-api-key"})
    assert reindex.status_code == 200
    assert reindex.json()["documents_indexed"] >= 4

    documents = client.get("/knowledge/documents")
    assert documents.status_code == 200
    assert len(documents.json()) >= 4

    search = client.get("/knowledge/search?query=refund%20payment")
    assert search.status_code == 200
    assert search.json()["results"]


def test_demo_seed_and_analytics(client: TestClient) -> None:
    unauthorized = client.post("/demo/seed")
    assert unauthorized.status_code == 401

    seed = client.post("/demo/seed", headers={"X-API-Key": "dev-api-key"})
    assert seed.status_code == 201
    assert len(seed.json()) == 3

    summary = client.get("/analytics/summary")
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["total_tickets"] == 3
    assert payload["escalations"] >= 2


def test_update_ticket_and_validation_errors(client: TestClient) -> None:
    invalid = client.post(
        "/tickets",
        json={"customer_email": "not-an-email", "subject": "Bad", "description": "This is valid enough."},
    )
    assert invalid.status_code == 422

    ticket = _create_ticket(client, "Cannot reset password", "I cannot reset my password because the link expired.")
    update = client.patch(f"/tickets/{ticket['id']}", json={"status": "open", "subject": "Password reset link expired"})
    assert update.status_code == 200
    assert update.json()["subject"] == "Password reset link expired"


def test_missing_resources_return_404(client: TestClient) -> None:
    assert client.get("/tickets/missing").status_code == 404
    assert client.post("/tickets/missing/workflow-runs").status_code == 404
    assert client.get("/workflow-runs/missing").status_code == 404


def test_workflow_definition(client: TestClient) -> None:
    response = client.get("/workflow/definition")
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "ai_support_ticket_resolution_graph"
    assert "rag_retriever" in payload["nodes"]


def _create_ticket(client: TestClient, subject: str, description: str) -> dict:
    response = client.post(
        "/tickets",
        json={
            "customer_email": "alex@example.com",
            "subject": subject,
            "description": description,
        },
    )
    assert response.status_code == 201
    return response.json()

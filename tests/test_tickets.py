import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.main import app
from app.repositories.ticket_repository import TicketRepository
from app.services.ticket_service import TicketService
from app.workflows.support_graph import SupportTicketWorkflow


@pytest.fixture()
def client(tmp_path) -> TestClient:
    database_path = tmp_path / "test_support_tickets.db"
    routes.ticket_service = TicketService(
        repository=TicketRepository(str(database_path)),
        workflow=SupportTicketWorkflow(),
    )
    return TestClient(app)


def test_create_and_get_ticket(client: TestClient) -> None:
    response = client.post(
        "/tickets",
        json={
            "customer_email": "alex@example.com",
            "subject": "Payment failed",
            "description": "My payment failed during checkout and I need help.",
        },
    )

    assert response.status_code == 201
    ticket = response.json()
    assert ticket["status"] == "open"

    get_response = client.get(f"/tickets/{ticket['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["subject"] == "Payment failed"


def test_analyze_ticket_classifies_category_and_priority(client: TestClient) -> None:
    ticket_id = _create_ticket(
        client,
        subject="API returns 500",
        description="Our production API endpoint returns 500 errors and customers are blocked.",
    )

    response = client.post(f"/tickets/{ticket_id}/analyze")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticket"]["status"] == "analyzed"
    assert payload["workflow"]["category"] == "api_error"
    assert payload["workflow"]["priority"] == "urgent"
    assert "production impact" in payload["workflow"]["risk_signals"]
    assert payload["workflow"]["workflow_steps"] == ["classifier", "knowledge_retriever"]


def test_resolve_ticket_can_escalate_high_impact_issue(client: TestClient) -> None:
    ticket_id = _create_ticket(
        client,
        subject="Money debited but order failed",
        description="The payment was debited from my bank, but the order failed.",
    )

    response = client.post(f"/tickets/{ticket_id}/resolve")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticket"]["status"] == "escalated"
    assert payload["workflow"]["escalation_required"] is True
    assert payload["workflow"]["drafted_response"]
    assert payload["workflow"]["recommended_actions"]
    assert payload["workflow"]["quality_score"] >= 0.66


def test_workflow_definition_and_summary_are_available(client: TestClient) -> None:
    seed_response = client.post("/demo/seed")
    assert seed_response.status_code == 201
    assert len(seed_response.json()) == 3

    workflow_response = client.get("/workflow/definition")
    assert workflow_response.status_code == 200
    workflow = workflow_response.json()
    assert workflow["name"] == "support_ticket_resolution_graph"
    assert "classifier" in workflow["nodes"]

    summary_response = client.get("/analytics/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["total_tickets"] == 3
    assert summary["escalations"] >= 2


def test_invalid_email_returns_422(client: TestClient) -> None:
    response = client.post(
        "/tickets",
        json={
            "customer_email": "not-an-email",
            "subject": "Payment failed",
            "description": "My payment failed during checkout and I need help.",
        },
    )

    assert response.status_code == 422


def test_missing_ticket_returns_404(client: TestClient) -> None:
    response = client.post("/tickets/missing/resolve")

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket not found"


def _create_ticket(client: TestClient, subject: str, description: str) -> str:
    response = client.post(
        "/tickets",
        json={
            "customer_email": "alex@example.com",
            "subject": subject,
            "description": description,
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])

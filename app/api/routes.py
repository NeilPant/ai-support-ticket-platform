from fastapi import APIRouter, HTTPException, status

from app.models.ticket import TicketCreate, TicketResponse, TicketSummary, TicketWorkflowResponse, WorkflowDefinition
from app.services.ticket_service import TicketService

router = APIRouter(tags=["tickets"])
ticket_service = TicketService()


@router.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(payload: TicketCreate) -> TicketResponse:
    return ticket_service.create_ticket(payload)


@router.get("/tickets", response_model=list[TicketResponse])
def list_tickets() -> list[TicketResponse]:
    return ticket_service.list_tickets()


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: str) -> TicketResponse:
    ticket = ticket_service.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


@router.post("/tickets/{ticket_id}/analyze", response_model=TicketWorkflowResponse)
def analyze_ticket(ticket_id: str) -> TicketWorkflowResponse:
    try:
        return ticket_service.analyze_ticket(ticket_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found") from exc


@router.post("/tickets/{ticket_id}/resolve", response_model=TicketWorkflowResponse)
def resolve_ticket(ticket_id: str) -> TicketWorkflowResponse:
    try:
        return ticket_service.resolve_ticket(ticket_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found") from exc


@router.get("/tickets/{ticket_id}/workflow-status", response_model=TicketWorkflowResponse)
def get_workflow_status(ticket_id: str) -> TicketWorkflowResponse:
    status_response = ticket_service.get_workflow_status(ticket_id)
    if status_response is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return status_response


@router.get("/analytics/summary", response_model=TicketSummary)
def get_ticket_summary() -> TicketSummary:
    return ticket_service.get_summary()


@router.get("/workflow/definition", response_model=WorkflowDefinition)
def get_workflow_definition() -> WorkflowDefinition:
    return ticket_service.get_workflow_definition()


@router.post("/demo/seed", response_model=list[TicketWorkflowResponse], status_code=status.HTTP_201_CREATED)
def seed_demo_tickets() -> list[TicketWorkflowResponse]:
    return ticket_service.seed_demo_tickets()

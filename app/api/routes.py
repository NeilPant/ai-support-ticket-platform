from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_ticket_service, require_api_key
from app.models.ticket import (
    KnowledgeDocument,
    KnowledgeReindexResponse,
    KnowledgeSearchResult,
    TicketCategory,
    TicketCreate,
    TicketListResponse,
    TicketPriority,
    TicketResponse,
    TicketStatus,
    TicketSummary,
    TicketUpdate,
    TicketWorkflowResponse,
    WorkflowDefinition,
    WorkflowRunResponse,
)
from app.services.ticket_service import TicketService

router = APIRouter()
ServiceDep = Annotated[TicketService, Depends(get_ticket_service)]


@router.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED, tags=["tickets"])
def create_ticket(payload: TicketCreate, service: ServiceDep) -> TicketResponse:
    return service.create_ticket(payload)


@router.get("/tickets", response_model=TicketListResponse, tags=["tickets"])
def list_tickets(
    service: ServiceDep,
    ticket_status: TicketStatus | None = Query(default=None, alias="status"),
    category: TicketCategory | None = None,
    priority: TicketPriority | None = None,
    escalation_required: bool | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TicketListResponse:
    return service.list_tickets(
        status=ticket_status,
        category=category,
        priority=priority,
        escalation_required=escalation_required,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/tickets/{ticket_id}", response_model=TicketResponse, tags=["tickets"])
def get_ticket(ticket_id: str, service: ServiceDep) -> TicketResponse:
    ticket = service.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


@router.patch("/tickets/{ticket_id}", response_model=TicketResponse, tags=["tickets"])
def update_ticket(ticket_id: str, payload: TicketUpdate, service: ServiceDep) -> TicketResponse:
    try:
        return service.update_ticket(ticket_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found") from exc


@router.post("/tickets/{ticket_id}/analyze", response_model=TicketWorkflowResponse, tags=["workflow"])
def analyze_ticket(ticket_id: str, service: ServiceDep) -> TicketWorkflowResponse:
    try:
        return service.analyze_ticket(ticket_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found") from exc


@router.post("/tickets/{ticket_id}/resolve", response_model=TicketWorkflowResponse, tags=["workflow"])
def resolve_ticket(ticket_id: str, service: ServiceDep) -> TicketWorkflowResponse:
    try:
        return service.resolve_ticket(ticket_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found") from exc


@router.post("/tickets/{ticket_id}/workflow-runs", response_model=TicketWorkflowResponse, tags=["workflow"])
def run_ticket_workflow(ticket_id: str, service: ServiceDep) -> TicketWorkflowResponse:
    try:
        return service.run_workflow(ticket_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found") from exc


@router.get("/tickets/{ticket_id}/workflow-runs", response_model=list[WorkflowRunResponse], tags=["workflow"])
def list_ticket_workflow_runs(ticket_id: str, service: ServiceDep) -> list[WorkflowRunResponse]:
    try:
        return service.list_workflow_runs(ticket_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found") from exc


@router.get("/workflow-runs/{run_id}", response_model=WorkflowRunResponse, tags=["workflow"])
def get_workflow_run(run_id: str, service: ServiceDep) -> WorkflowRunResponse:
    run = service.get_workflow_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow run not found")
    return run


@router.get("/tickets/{ticket_id}/workflow-status", response_model=TicketWorkflowResponse, tags=["workflow"])
def get_workflow_status(ticket_id: str, service: ServiceDep) -> TicketWorkflowResponse:
    status_response = service.get_workflow_status(ticket_id)
    if status_response is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return status_response


@router.get("/analytics/summary", response_model=TicketSummary, tags=["analytics"])
def get_ticket_summary(service: ServiceDep) -> TicketSummary:
    return service.get_summary()


@router.get("/workflow/definition", response_model=WorkflowDefinition, tags=["workflow"])
def get_workflow_definition(service: ServiceDep) -> WorkflowDefinition:
    return service.get_workflow_definition()


@router.post(
    "/demo/seed",
    response_model=list[TicketWorkflowResponse],
    status_code=status.HTTP_201_CREATED,
    tags=["demo"],
    dependencies=[Depends(require_api_key)],
)
def seed_demo_tickets(service: ServiceDep) -> list[TicketWorkflowResponse]:
    return service.seed_demo_tickets()


@router.post(
    "/knowledge/reindex",
    response_model=KnowledgeReindexResponse,
    tags=["knowledge"],
    dependencies=[Depends(require_api_key)],
)
def reindex_knowledge(service: ServiceDep) -> KnowledgeReindexResponse:
    return service.reindex_knowledge()


@router.get("/knowledge/documents", response_model=list[KnowledgeDocument], tags=["knowledge"])
def list_knowledge_documents(service: ServiceDep) -> list[KnowledgeDocument]:
    return service.list_knowledge_documents()


@router.get("/knowledge/search", response_model=KnowledgeSearchResult, tags=["knowledge"])
def search_knowledge(
    service: ServiceDep,
    query: str = Query(min_length=2),
    limit: int = Query(default=5, ge=1, le=10),
) -> KnowledgeSearchResult:
    return service.search_knowledge(query=query, limit=limit)

from app.models.ticket import (
    KnowledgeDocument,
    KnowledgeReindexResponse,
    KnowledgeSearchResult,
    Ticket,
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
    WorkflowResult,
    WorkflowRunResponse,
)
from app.repositories.ticket_repository import TicketRepository
from app.services.knowledge_service import KnowledgeService
from app.workflows.support_graph import SupportTicketWorkflow


class TicketService:
    def __init__(
        self,
        repository: TicketRepository,
        workflow: SupportTicketWorkflow,
        knowledge_service: KnowledgeService,
    ) -> None:
        self.repository = repository
        self.workflow = workflow
        self.knowledge_service = knowledge_service

    def create_ticket(self, payload: TicketCreate) -> TicketResponse:
        ticket = Ticket(**payload.model_dump())
        created = self.repository.create(ticket)
        self.repository.add_audit_event("ticket", created.id, "created", {"subject": created.subject})
        return TicketResponse(**created.model_dump())

    def list_tickets(
        self,
        *,
        status: TicketStatus | None = None,
        category: TicketCategory | None = None,
        priority: TicketPriority | None = None,
        escalation_required: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> TicketListResponse:
        tickets, total = self.repository.list(
            status=status,
            category=category,
            priority=priority,
            escalation_required=escalation_required,
            search=search,
            limit=limit,
            offset=offset,
        )
        return TicketListResponse(
            items=[TicketResponse(**ticket.model_dump()) for ticket in tickets],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_ticket(self, ticket_id: str) -> TicketResponse | None:
        ticket = self.repository.get(ticket_id)
        if ticket is None:
            return None
        return TicketResponse(**ticket.model_dump())

    def update_ticket(self, ticket_id: str, payload: TicketUpdate) -> TicketResponse:
        ticket = self._get_existing_ticket(ticket_id)
        updates = payload.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(ticket, key, value)
        saved = self.repository.save(ticket)
        self.repository.add_audit_event("ticket", saved.id, "updated", updates)
        return TicketResponse(**saved.model_dump())

    def analyze_ticket(self, ticket_id: str) -> TicketWorkflowResponse:
        ticket = self._get_existing_ticket(ticket_id)
        result = self.workflow.analyze(ticket)
        ticket.status = TicketStatus.analyzed
        ticket.category = result.category
        ticket.priority = result.priority
        saved = self.repository.save(ticket)
        run = self.repository.create_workflow_run(result)
        result.run_id = run.id
        return TicketWorkflowResponse(ticket=TicketResponse(**saved.model_dump()), workflow=result)

    def resolve_ticket(self, ticket_id: str) -> TicketWorkflowResponse:
        return self.run_workflow(ticket_id)

    def run_workflow(self, ticket_id: str) -> TicketWorkflowResponse:
        ticket = self._get_existing_ticket(ticket_id)
        result = self.workflow.run(ticket)
        ticket.status = result.status
        ticket.category = result.category
        ticket.priority = result.priority
        ticket.escalation_required = result.escalation_required
        saved = self.repository.save(ticket)
        run = self.repository.create_workflow_run(result)
        result.run_id = run.id
        return TicketWorkflowResponse(ticket=TicketResponse(**saved.model_dump()), workflow=result)

    def get_workflow_status(self, ticket_id: str) -> TicketWorkflowResponse | None:
        ticket = self.repository.get(ticket_id)
        if ticket is None:
            return None
        result = self.repository.latest_workflow_result(ticket.id) or WorkflowResult(
            ticket_id=ticket.id,
            status=ticket.status,
        )
        return TicketWorkflowResponse(ticket=TicketResponse(**ticket.model_dump()), workflow=result)

    def list_workflow_runs(self, ticket_id: str) -> list[WorkflowRunResponse]:
        self._get_existing_ticket(ticket_id)
        return self.repository.list_workflow_runs_for_ticket(ticket_id)

    def get_workflow_run(self, run_id: str) -> WorkflowRunResponse | None:
        return self.repository.get_workflow_run(run_id)

    def get_summary(self) -> TicketSummary:
        tickets, _total = self.repository.list(limit=10_000)
        workflows = self.repository.list_workflow_results()
        by_status = {status.value: 0 for status in TicketStatus}
        by_category: dict[str, int] = {}
        for ticket in tickets:
            by_status[ticket.status.value] += 1
        escalations = 0
        for workflow in workflows:
            if workflow.category:
                by_category[workflow.category.value] = by_category.get(workflow.category.value, 0) + 1
            if workflow.escalation_required:
                escalations += 1
        return TicketSummary(
            total_tickets=len(tickets),
            by_status=by_status,
            by_category=by_category,
            escalations=escalations,
        )

    def get_workflow_definition(self) -> WorkflowDefinition:
        return WorkflowDefinition.model_validate(self.workflow.describe())

    def seed_demo_tickets(self) -> list[TicketWorkflowResponse]:
        samples = [
            TicketCreate(
                customer_email="billing.customer@example.com",
                subject="Money debited but order failed",
                description="The payment was debited from my bank, but the order failed during checkout.",
            ),
            TicketCreate(
                customer_email="platform.lead@example.com",
                subject="Production API returns 500",
                description="Our production API endpoint returns 500 errors and customers are blocked.",
            ),
            TicketCreate(
                customer_email="user@example.com",
                subject="Cannot reset password",
                description="I cannot reset my password because the reset link keeps expiring.",
            ),
        ]
        return [self.run_workflow(self.create_ticket(sample).id) for sample in samples]

    def reindex_knowledge(self) -> KnowledgeReindexResponse:
        return self.knowledge_service.reindex()

    def list_knowledge_documents(self) -> list[KnowledgeDocument]:
        return self.knowledge_service.list_documents()

    def search_knowledge(self, query: str, limit: int = 5) -> KnowledgeSearchResult:
        self.knowledge_service.ensure_indexed()
        return self.knowledge_service.search(query, limit=limit)

    def knowledge_ready(self) -> bool:
        return self.repository.knowledge_index_ready()

    def _get_existing_ticket(self, ticket_id: str) -> Ticket:
        ticket = self.repository.get(ticket_id)
        if ticket is None:
            raise KeyError(ticket_id)
        return ticket

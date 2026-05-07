from app.models.ticket import (
    Ticket,
    TicketCreate,
    TicketResponse,
    TicketStatus,
    TicketSummary,
    TicketWorkflowResponse,
    WorkflowDefinition,
    WorkflowResult,
)
from app.repositories.ticket_repository import TicketRepository
from app.workflows.support_graph import SupportTicketWorkflow


class TicketService:
    def __init__(
        self,
        repository: TicketRepository | None = None,
        workflow: SupportTicketWorkflow | None = None,
    ) -> None:
        self.repository = repository or TicketRepository()
        self.workflow = workflow or SupportTicketWorkflow()

    def create_ticket(self, payload: TicketCreate) -> TicketResponse:
        ticket = Ticket(**payload.model_dump())
        return TicketResponse(**self.repository.create(ticket).model_dump())

    def list_tickets(self) -> list[TicketResponse]:
        return [TicketResponse(**ticket.model_dump()) for ticket in self.repository.list()]

    def get_ticket(self, ticket_id: str) -> TicketResponse | None:
        ticket = self.repository.get(ticket_id)
        if ticket is None:
            return None
        return TicketResponse(**ticket.model_dump())

    def analyze_ticket(self, ticket_id: str) -> TicketWorkflowResponse:
        ticket = self._get_existing_ticket(ticket_id)
        result = self.workflow.analyze(ticket)
        ticket.status = TicketStatus.analyzed
        ticket = self.repository.save(ticket)
        self.repository.save_workflow_result(result)
        return TicketWorkflowResponse(ticket=TicketResponse(**ticket.model_dump()), workflow=result)

    def resolve_ticket(self, ticket_id: str) -> TicketWorkflowResponse:
        ticket = self._get_existing_ticket(ticket_id)
        result = self.workflow.run(ticket)
        ticket.status = result.status
        ticket = self.repository.save(ticket)
        self.repository.save_workflow_result(result)
        return TicketWorkflowResponse(ticket=TicketResponse(**ticket.model_dump()), workflow=result)

    def get_workflow_status(self, ticket_id: str) -> TicketWorkflowResponse | None:
        ticket = self.repository.get(ticket_id)
        if ticket is None:
            return None

        result = self.repository.get_workflow_result(ticket.id) or WorkflowResult(ticket_id=ticket.id, status=ticket.status)
        return TicketWorkflowResponse(ticket=TicketResponse(**ticket.model_dump()), workflow=result)

    def get_summary(self) -> TicketSummary:
        tickets = self.repository.list()
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

        responses: list[TicketWorkflowResponse] = []
        for sample in samples:
            ticket = self.create_ticket(sample)
            responses.append(self.resolve_ticket(ticket.id))
        return responses

    def _get_existing_ticket(self, ticket_id: str) -> Ticket:
        ticket = self.repository.get(ticket_id)
        if ticket is None:
            raise KeyError(ticket_id)
        return ticket

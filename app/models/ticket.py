from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field


class TicketStatus(str, Enum):
    open = "open"
    analyzed = "analyzed"
    resolved = "resolved"
    escalated = "escalated"


class TicketCategory(str, Enum):
    billing = "billing"
    authentication = "authentication"
    api_error = "api_error"
    performance = "performance"
    general = "general"


class TicketPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TicketCreate(BaseModel):
    customer_email: EmailStr = Field(..., examples=["alex@example.com"])
    subject: str = Field(..., min_length=3, examples=["Payment failed during checkout"])
    description: str = Field(..., min_length=10)


class Ticket(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    customer_email: EmailStr
    subject: str
    description: str
    status: TicketStatus = TicketStatus.open
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkflowResult(BaseModel):
    ticket_id: str
    status: TicketStatus
    category: TicketCategory | None = None
    priority: TicketPriority | None = None
    knowledge_snippets: list[str] = Field(default_factory=list)
    drafted_response: str | None = None
    escalation_required: bool = False
    escalation_reason: str | None = None
    quality_score: float | None = None
    risk_signals: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    workflow_steps: list[str] = Field(default_factory=list)


class TicketResponse(Ticket):
    pass


class TicketWorkflowResponse(BaseModel):
    ticket: TicketResponse
    workflow: WorkflowResult


class WorkflowDefinition(BaseModel):
    name: str
    nodes: list[str]
    edges: list[tuple[str, str]]


class TicketSummary(BaseModel):
    total_tickets: int
    by_status: dict[str, int]
    by_category: dict[str, int]
    escalations: int

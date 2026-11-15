from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field, field_validator
from pydantic.json_schema import SkipJsonSchema


class TicketStatus(StrEnum):
    open = "open"
    analyzed = "analyzed"
    resolved = "resolved"
    escalated = "escalated"


class TicketCategory(StrEnum):
    billing = "billing"
    authentication = "authentication"
    api_error = "api_error"
    performance = "performance"
    general = "general"


class TicketPriority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TicketCreate(BaseModel):
    customer_email: EmailStr = Field(..., examples=["alex@example.com"])
    subject: str = Field(..., min_length=3, max_length=200, examples=["Payment failed during checkout"])
    description: str = Field(..., min_length=10, max_length=5000)


class TicketUpdate(BaseModel):
    status: TicketStatus | SkipJsonSchema[None] = Field(default_factory=lambda: None)
    subject: str | SkipJsonSchema[None] = Field(default_factory=lambda: None, min_length=3, max_length=200)
    description: str | SkipJsonSchema[None] = Field(default_factory=lambda: None, min_length=10, max_length=5000)

    @field_validator("status", "subject", "description", mode="before")
    @classmethod
    def reject_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("Omit this field to leave its current value")
        return value


class Ticket(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    customer_email: EmailStr
    subject: str
    description: str
    status: TicketStatus = TicketStatus.open
    category: TicketCategory | None = None
    priority: TicketPriority | None = None
    escalation_required: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ClassificationResult(BaseModel):
    category: TicketCategory
    priority: TicketPriority
    sentiment: str = "neutral"
    urgency_score: float = Field(default=0.5, ge=0, le=1)
    confidence: float = Field(default=0.75, ge=0, le=1)
    risk_signals: list[str] = Field(default_factory=list)


class RetrievedContext(BaseModel):
    document_id: str
    title: str
    content: str
    score: float = Field(ge=0)
    source_path: str


class ResolutionPlan(BaseModel):
    summary: str
    next_steps: list[str] = Field(default_factory=list)
    customer_questions: list[str] = Field(default_factory=list)
    internal_notes: list[str] = Field(default_factory=list)


class EscalationDecision(BaseModel):
    required: bool = False
    reason: str | None = None
    target_team: str | None = None


class QualityReview(BaseModel):
    score: float = Field(default=0, ge=0, le=1)
    passed: bool = False
    issues: list[str] = Field(default_factory=list)


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class WorkflowResult(BaseModel):
    ticket_id: str
    run_id: str | None = None
    trace_id: str | None = None
    status: TicketStatus
    category: TicketCategory | None = None
    priority: TicketPriority | None = None
    classification: ClassificationResult | None = None
    retrieved_context: list[RetrievedContext] = Field(default_factory=list)
    knowledge_snippets: list[str] = Field(default_factory=list)
    resolution_plan: ResolutionPlan | None = None
    drafted_response: str | None = None
    escalation_decision: EscalationDecision = Field(default_factory=EscalationDecision)
    escalation_required: bool = False
    escalation_reason: str | None = None
    quality_review: QualityReview | None = None
    quality_score: float | None = None
    risk_signals: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    workflow_steps: list[str] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)


class TicketResponse(Ticket):
    pass


class TicketListResponse(BaseModel):
    items: list[TicketResponse]
    total: int
    limit: int
    offset: int


class WorkflowStepResponse(BaseModel):
    position: int
    name: str
    status: str
    summary: str | None = None
    created_at: datetime


class WorkflowRunResponse(BaseModel):
    id: str
    ticket_id: str
    status: TicketStatus
    trace_id: str
    result: WorkflowResult
    steps: list[WorkflowStepResponse] = Field(default_factory=list)
    created_at: datetime


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


class KnowledgeDocument(BaseModel):
    id: str
    title: str
    source_path: str
    checksum: str
    updated_at: datetime


class KnowledgeSearchResult(BaseModel):
    query: str
    results: list[RetrievedContext]


class KnowledgeReindexResponse(BaseModel):
    documents_indexed: int
    chunks_indexed: int


class ReadinessResponse(BaseModel):
    status: str
    database: bool
    knowledge_index: bool
    llm_mode: str


class ErrorResponse(BaseModel):
    error: str
    detail: str
    request_id: str | None = None

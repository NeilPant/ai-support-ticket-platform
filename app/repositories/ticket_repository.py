from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.ticket import (
    KnowledgeDocument,
    Ticket,
    TicketCategory,
    TicketPriority,
    TicketStatus,
    WorkflowResult,
    WorkflowRunResponse,
    WorkflowStepResponse,
)
from app.repositories.orm_models import (
    AuditEventRecord,
    KnowledgeChunkRecord,
    KnowledgeDocumentRecord,
    TicketRecord,
    WorkflowRunRecord,
    WorkflowStepRecord,
)


class TicketRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, ticket: Ticket) -> Ticket:
        record = TicketRecord(
            id=ticket.id,
            customer_email=str(ticket.customer_email),
            subject=ticket.subject,
            description=ticket.description,
            status=ticket.status.value,
            category=ticket.category.value if ticket.category else None,
            priority=ticket.priority.value if ticket.priority else None,
            escalation_required=ticket.escalation_required,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return self._ticket_from_record(record)

    def get(self, ticket_id: str) -> Ticket | None:
        record = self.session.get(TicketRecord, ticket_id)
        return self._ticket_from_record(record) if record else None

    def list(
        self,
        *,
        status: TicketStatus | None = None,
        category: TicketCategory | None = None,
        priority: TicketPriority | None = None,
        escalation_required: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Ticket], int]:
        statement = select(TicketRecord)
        count_statement = select(func.count()).select_from(TicketRecord)

        filters = []
        if status:
            filters.append(TicketRecord.status == status.value)
        if category:
            filters.append(TicketRecord.category == category.value)
        if priority:
            filters.append(TicketRecord.priority == priority.value)
        if escalation_required is not None:
            filters.append(TicketRecord.escalation_required == escalation_required)
        if search:
            like = f"%{search.lower()}%"
            filters.append(
                or_(
                    func.lower(TicketRecord.subject).like(like),
                    func.lower(TicketRecord.description).like(like),
                    func.lower(TicketRecord.customer_email).like(like),
                )
            )

        for item in filters:
            statement = statement.where(item)
            count_statement = count_statement.where(item)

        total = int(self.session.execute(count_statement).scalar_one())
        rows = self.session.execute(
            statement.order_by(TicketRecord.created_at.desc()).limit(limit).offset(offset)
        ).scalars()
        return [self._ticket_from_record(row) for row in rows], total

    def save(self, ticket: Ticket, *, commit: bool = True) -> Ticket:
        record = self.session.get(TicketRecord, ticket.id)
        if record is None:
            raise KeyError(ticket.id)
        record.customer_email = str(ticket.customer_email)
        record.subject = ticket.subject
        record.description = ticket.description
        record.status = ticket.status.value
        record.category = ticket.category.value if ticket.category else None
        record.priority = ticket.priority.value if ticket.priority else None
        record.escalation_required = ticket.escalation_required
        record.updated_at = datetime.now(UTC)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        self.session.refresh(record)
        return self._ticket_from_record(record)

    def create_workflow_run(self, result: WorkflowResult) -> WorkflowRunResponse:
        run_id = result.run_id or str(uuid4())
        trace_id = result.trace_id or str(uuid4())
        result.run_id = run_id
        result.trace_id = trace_id
        record = WorkflowRunRecord(
            id=run_id,
            ticket_id=result.ticket_id,
            status=result.status.value,
            trace_id=trace_id,
            payload_json=result.model_dump_json(),
            token_usage_json=result.token_usage.model_dump_json(),
        )
        self.session.add(record)
        self.session.flush()
        for position, step_name in enumerate(result.workflow_steps, start=1):
            self.session.add(
                WorkflowStepRecord(
                    run_id=run_id,
                    position=position,
                    name=step_name,
                    status="completed",
                    summary=self._step_summary(step_name, result),
                )
            )
        self.add_audit_event("workflow_run", run_id, "created", {"ticket_id": result.ticket_id}, commit=False)
        self.session.commit()
        return self.get_workflow_run(run_id)  # type: ignore[return-value]

    def latest_workflow_result(self, ticket_id: str) -> WorkflowResult | None:
        run = self.session.execute(
            select(WorkflowRunRecord)
            .where(WorkflowRunRecord.ticket_id == ticket_id)
            .order_by(WorkflowRunRecord.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        return WorkflowResult.model_validate_json(run.payload_json) if run else None

    def list_workflow_results(self) -> list[WorkflowResult]:
        rows = self.session.execute(select(WorkflowRunRecord).order_by(WorkflowRunRecord.created_at.desc())).scalars()
        return [WorkflowResult.model_validate_json(row.payload_json) for row in rows]

    def list_workflow_runs_for_ticket(self, ticket_id: str) -> list[WorkflowRunResponse]:
        rows = self.session.execute(
            select(WorkflowRunRecord)
            .where(WorkflowRunRecord.ticket_id == ticket_id)
            .options(selectinload(WorkflowRunRecord.steps))
            .order_by(WorkflowRunRecord.created_at.desc())
        ).scalars()
        return [self._run_from_record(row) for row in rows]

    def get_workflow_run(self, run_id: str) -> WorkflowRunResponse | None:
        row = self.session.execute(
            select(WorkflowRunRecord)
            .where(WorkflowRunRecord.id == run_id)
            .options(selectinload(WorkflowRunRecord.steps))
        ).scalar_one_or_none()
        return self._run_from_record(row) if row else None

    def replace_knowledge_index(
        self,
        documents: list[KnowledgeDocumentRecord],
        chunks: list[KnowledgeChunkRecord],
    ) -> tuple[int, int]:
        self.session.query(KnowledgeChunkRecord).delete()
        self.session.query(KnowledgeDocumentRecord).delete()
        self.session.add_all(documents)
        self.session.flush()
        self.session.add_all(chunks)
        self.add_audit_event(
            "knowledge_base",
            "local",
            "reindexed",
            {"documents": len(documents), "chunks": len(chunks)},
            commit=False,
        )
        self.session.commit()
        return len(documents), len(chunks)

    def list_knowledge_documents(self) -> list[KnowledgeDocument]:
        rows = self.session.execute(select(KnowledgeDocumentRecord).order_by(KnowledgeDocumentRecord.title)).scalars()
        return [
            KnowledgeDocument(
                id=row.id,
                title=row.title,
                source_path=row.source_path,
                checksum=row.checksum,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    def list_knowledge_chunks(self) -> list[KnowledgeChunkRecord]:
        return list(
            self.session.execute(
                select(KnowledgeChunkRecord).options(selectinload(KnowledgeChunkRecord.document))
            ).scalars()
        )

    def knowledge_index_ready(self) -> bool:
        return self.session.execute(select(func.count()).select_from(KnowledgeChunkRecord)).scalar_one() > 0

    def add_audit_event(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        payload: dict,
        *,
        commit: bool = True,
    ) -> None:
        self.session.add(
            AuditEventRecord(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                payload_json=json.dumps(payload),
            )
        )
        if commit:
            self.session.commit()

    def _ticket_from_record(self, record: TicketRecord) -> Ticket:
        return Ticket(
            id=record.id,
            customer_email=record.customer_email,
            subject=record.subject,
            description=record.description,
            status=TicketStatus(record.status),
            category=TicketCategory(record.category) if record.category else None,
            priority=TicketPriority(record.priority) if record.priority else None,
            escalation_required=record.escalation_required,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _run_from_record(self, row: WorkflowRunRecord) -> WorkflowRunResponse:
        result = WorkflowResult.model_validate_json(row.payload_json)
        return WorkflowRunResponse(
            id=row.id,
            ticket_id=row.ticket_id,
            status=TicketStatus(row.status),
            trace_id=row.trace_id,
            result=result,
            steps=[
                WorkflowStepResponse(
                    position=step.position,
                    name=step.name,
                    status=step.status,
                    summary=step.summary,
                    created_at=step.created_at,
                )
                for step in row.steps
            ],
            created_at=row.created_at,
        )

    def _step_summary(self, step_name: str, result: WorkflowResult) -> str:
        summaries = {
            "intake_validator": "Validated ticket content and required fields.",
            "classifier": f"Classified as {result.category} / {result.priority}.",
            "rag_retriever": f"Retrieved {len(result.retrieved_context)} knowledge chunks.",
            "resolution_planner": "Generated support plan and recommended actions.",
            "response_writer": "Drafted customer-facing response.",
            "escalation_decider": "Evaluated escalation policy.",
            "quality_guardrail": f"Quality score {result.quality_score}.",
            "audit_logger": "Recorded workflow audit metadata.",
        }
        return summaries.get(step_name, "Completed workflow step.")

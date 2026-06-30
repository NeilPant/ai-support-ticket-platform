from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.repositories.ticket_repository import TicketRepository
from app.services.knowledge_service import KnowledgeService
from app.services.llm_service import LLMService
from app.services.ticket_service import TicketService
from app.workflows.support_graph import SupportTicketWorkflow


def get_repository(db: Annotated[Session, Depends(get_db)]) -> TicketRepository:
    return TicketRepository(db)


def get_knowledge_service(repository: Annotated[TicketRepository, Depends(get_repository)]) -> KnowledgeService:
    return KnowledgeService(repository)


def get_ticket_service(
    repository: Annotated[TicketRepository, Depends(get_repository)],
    knowledge_service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> TicketService:
    workflow = SupportTicketWorkflow(knowledge_service=knowledge_service, llm_service=LLMService())
    return TicketService(repository=repository, workflow=workflow, knowledge_service=knowledge_service)


def require_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")

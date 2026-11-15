from __future__ import annotations

import hashlib
import re
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.core.config import get_settings
from app.models.ticket import KnowledgeDocument, KnowledgeReindexResponse, KnowledgeSearchResult, RetrievedContext
from app.repositories.orm_models import KnowledgeChunkRecord, KnowledgeDocumentRecord, utc_now
from app.repositories.ticket_repository import TicketRepository


class KnowledgeService:
    def __init__(self, repository: TicketRepository, base_path: str | None = None) -> None:
        self.repository = repository
        self.base_path = Path(base_path or get_settings().knowledge_base_path)

    def reindex(self) -> KnowledgeReindexResponse:
        documents: list[KnowledgeDocumentRecord] = []
        chunks: list[KnowledgeChunkRecord] = []

        for path in sorted(self.base_path.iterdir()):
            if not path.match("*.md"):
                continue
            content = path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
            document_id = str(uuid5(NAMESPACE_URL, str(path.resolve())))
            title = self._extract_title(content, path)
            documents.append(
                KnowledgeDocumentRecord(
                    id=document_id,
                    title=title,
                    source_path=str(path),
                    checksum=checksum,
                    updated_at=utc_now(),
                )
            )
            for index, chunk in enumerate(self._chunk_text(content)):
                chunks.append(
                    KnowledgeChunkRecord(
                        id=str(uuid5(NAMESPACE_URL, f"{document_id}:{index}:{checksum}")),
                        document_id=document_id,
                        chunk_index=index,
                        content=chunk,
                        token_count=len(chunk.split()),
                    )
                )

        document_count, chunk_count = self.repository.replace_knowledge_index(documents, chunks)
        return KnowledgeReindexResponse(documents_indexed=document_count, chunks_indexed=chunk_count)

    def list_documents(self) -> list[KnowledgeDocument]:
        return self.repository.list_knowledge_documents()

    def search(self, query: str, limit: int = 5) -> KnowledgeSearchResult:
        query_terms = self._terms(query)
        results: list[RetrievedContext] = []
        for chunk in self.repository.list_knowledge_chunks():
            content_terms = self._terms(chunk.content)
            if not content_terms:
                continue
            overlap = query_terms.intersection(content_terms)
            phrase_bonus = 1 if query.lower() in chunk.content.lower() else 0
            score = (len(overlap) / max(len(query_terms), 1)) + phrase_bonus
            if score <= 0:
                continue
            results.append(
                RetrievedContext(
                    document_id=chunk.document_id,
                    title=chunk.document.title,
                    content=chunk.content,
                    score=round(score, 3),
                    source_path=chunk.document.source_path,
                )
            )

        results.sort(key=lambda item: item.score, reverse=True)
        return KnowledgeSearchResult(query=query, results=results[:limit])

    def ensure_indexed(self) -> None:
        if not self.repository.knowledge_index_ready():
            self.reindex()

    def _extract_title(self, content: str, path: Path) -> str:
        for line in content.splitlines():
            if line.startswith("# "):
                return line.removeprefix("# ").strip()
        return path.stem.replace("_", " ").title()

    def _chunk_text(self, content: str, max_words: int = 90) -> list[str]:
        paragraphs = [item.strip() for item in re.split(r"\n\s*\n", content) if item.strip()]
        chunks: list[str] = []
        current: list[str] = []
        for paragraph in paragraphs:
            words = paragraph.split()
            for start in range(0, len(words), max_words):
                part = words[start : start + max_words]
                if current and len(current) + len(part) > max_words:
                    chunks.append(" ".join(current))
                    current = []
                current.extend(part)
        if current:
            chunks.append(" ".join(current))
        return chunks

    def _terms(self, text: str) -> set[str]:
        stopwords = {"the", "and", "or", "to", "a", "of", "for", "is", "in", "with", "before"}
        return {term for term in re.findall(r"[a-zA-Z0-9]+", text.lower()) if term not in stopwords}

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from app.core.config import get_settings
from app.models.ticket import Ticket, WorkflowResult


class TicketRepository:
    """SQLite-backed repository for tickets and workflow results."""

    def __init__(self, database_path: str | None = None) -> None:
        self.database_path = database_path or get_settings().database_path
        self._lock = RLock()
        self._initialize_database()

    def create(self, ticket: Ticket) -> Ticket:
        payload = ticket.model_dump(mode="json")
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tickets (
                    id, customer_email, subject, description, status, created_at, updated_at
                )
                VALUES (:id, :customer_email, :subject, :description, :status, :created_at, :updated_at)
                """,
                payload,
            )
        return ticket

    def get(self, ticket_id: str) -> Ticket | None:
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return self._row_to_ticket(row) if row else None

    def list(self) -> list[Ticket]:
        with self._lock, self._connect() as connection:
            rows = connection.execute("SELECT * FROM tickets ORDER BY created_at DESC").fetchall()
        return [self._row_to_ticket(row) for row in rows]

    def save(self, ticket: Ticket) -> Ticket:
        ticket.updated_at = datetime.now(timezone.utc)
        payload = ticket.model_dump(mode="json")
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE tickets
                SET customer_email = :customer_email,
                    subject = :subject,
                    description = :description,
                    status = :status,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                payload,
            )
        return ticket

    def save_workflow_result(self, result: WorkflowResult) -> WorkflowResult:
        payload = result.model_dump(mode="json")
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO workflow_results (ticket_id, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(ticket_id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (result.ticket_id, json.dumps(payload), now),
            )
        return result

    def get_workflow_result(self, ticket_id: str) -> WorkflowResult | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM workflow_results WHERE ticket_id = ?",
                (ticket_id,),
            ).fetchone()
        if row is None:
            return None
        return WorkflowResult.model_validate(json.loads(row["payload"]))

    def list_workflow_results(self) -> list[WorkflowResult]:
        with self._lock, self._connect() as connection:
            rows = connection.execute("SELECT payload FROM workflow_results").fetchall()
        return [WorkflowResult.model_validate(json.loads(row["payload"])) for row in rows]

    def _initialize_database(self) -> None:
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)

        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY,
                    customer_email TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS workflow_results (
                    ticket_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _row_to_ticket(self, row: sqlite3.Row) -> Ticket:
        return Ticket.model_validate(dict(row))

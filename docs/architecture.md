# Architecture

## Goal

This project demonstrates a production-shaped FastAPI backend for AI-assisted customer support operations. It keeps the core workflow deterministic by default so the project can be tested and showcased without paid API keys.

## Request Flow

1. A user creates a support ticket through `POST /tickets`.
2. The ticket is persisted in SQLite.
3. `POST /tickets/{ticket_id}/resolve` runs the LangGraph workflow.
4. The workflow result is stored with the ticket.
5. Analytics endpoints summarize ticket status, categories, and escalations.

## LangGraph Nodes

- `classifier`: predicts ticket category and priority.
- `knowledge_retriever`: retrieves category-specific support guidance.
- `resolution_writer`: drafts a customer response.
- `escalation_router`: decides whether a human should review the ticket.
- `quality_checker`: scores the drafted response for basic support quality.

## Persistence

The repository uses SQLite through Python's standard library. This keeps the app lightweight while still demonstrating real persistence, schema creation, and repository boundaries.

## Cloud Readiness

The app is container-ready with `Dockerfile`. For AWS, Azure, or GCP, deploy the container and mount persistent storage or replace SQLite with a managed PostgreSQL database.

# Architecture

## Goal

This project demonstrates a production-shaped FastAPI backend for AI-assisted customer support operations. It keeps every AI node deterministic by default so the project can be tested and showcased without paid API keys, while still supporting OpenAI-backed LangChain calls when configured.

## Request Flow

1. A user creates a support ticket through `POST /tickets`.
2. The ticket is persisted in SQLite.
3. `POST /tickets/{ticket_id}/workflow-runs` runs the LangGraph workflow.
4. The workflow retrieves local support playbook context from the indexed knowledge base.
5. Workflow runs, step history, RAG context, and audit events are persisted.
6. Analytics endpoints summarize ticket status, categories, and escalations.

## LangGraph Nodes

- `intake_validator`: validates ticket content.
- `classifier`: predicts category, priority, sentiment, urgency, confidence, and risk signals.
- `rag_retriever`: retrieves local knowledge-base chunks.
- `resolution_planner`: creates next steps, questions, and internal notes.
- `response_writer`: drafts a customer response.
- `escalation_decider`: decides whether a human should review the ticket.
- `quality_guardrail`: scores the drafted response for support quality and safety.
- `audit_logger`: records workflow trace metadata.

## Persistence

The repository uses SQLAlchemy with SQLite locally and can point at PostgreSQL through `DATABASE_URL` on Render.

## Cloud Readiness

The app is container-ready with `Dockerfile`. The recommended portfolio deployment is Render Web Service plus Render PostgreSQL.

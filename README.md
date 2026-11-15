# AI Support Ticket Resolution Platform

A professional FastAPI backend for AI-assisted customer support. It demonstrates LangGraph agent orchestration, LangChain/OpenAI structured outputs, local RAG over support playbooks, persisted workflow runs, API-key protected admin endpoints, SQLAlchemy persistence, CI, Docker, and Render-ready deployment.

The app works in two modes:

- **Deterministic fallback mode**: no API key required; ideal for tests and demos.
- **OpenAI mode**: set `USE_LLM=true` and `OPENAI_API_KEY` to enable LangChain-backed classification, planning, and response drafting.

## Architecture

```text
FastAPI API
  -> Ticket Service
  -> SQLAlchemy Repository
  -> LangGraph Workflow
      -> intake_validator
      -> classifier
      -> rag_retriever
      -> resolution_planner
      -> response_writer
      -> escalation_decider
      -> quality_guardrail
      -> audit_logger
  -> SQLite locally / PostgreSQL on Render
```

## What It Shows

- REST API design with FastAPI and Pydantic
- LangGraph multi-node AI workflow
- LangChain prompt composition and optional OpenAI structured outputs
- Local RAG over markdown support playbooks
- Persisted tickets, workflow runs, workflow steps, knowledge chunks, and audit events
- API-key authentication for admin/demo operations
- Request IDs, readiness checks, Docker, CI, and deployment documentation

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Demo Flow

Index the local knowledge base:

```bash
curl -X POST http://127.0.0.1:8000/knowledge/reindex -H "X-API-Key: dev-api-key"
```

Seed demo tickets and workflow runs:

```bash
curl -X POST http://127.0.0.1:8000/demo/seed -H "X-API-Key: dev-api-key"
```

Search the support playbooks:

```bash
curl "http://127.0.0.1:8000/knowledge/search?query=production%20api%20500"
```

View analytics:

```bash
curl http://127.0.0.1:8000/analytics/summary
```

## Main Endpoints

```text
GET    /health
GET    /readiness
POST   /tickets
GET    /tickets?status=&category=&priority=&escalation_required=&search=&limit=&offset=
GET    /tickets/{ticket_id}
PATCH  /tickets/{ticket_id}
POST   /tickets/{ticket_id}/workflow-runs
GET    /tickets/{ticket_id}/workflow-runs
GET    /workflow-runs/{run_id}
GET    /workflow/definition
POST   /knowledge/reindex
GET    /knowledge/documents
GET    /knowledge/search?query=...
POST   /demo/seed
GET    /analytics/summary
```

`/health` reports whether the API process is running. `/readiness` returns HTTP 503 when the database is unavailable.

## Optional OpenAI Mode

```bash
pip install langchain-openai
$env:OPENAI_API_KEY="your-key"
$env:USE_LLM="true"
uvicorn app.main:app --reload
```

If OpenAI is unavailable, each AI node falls back to deterministic behavior so the project remains functional.

## Test And Quality

```bash
pytest
ruff check .
```

CI runs tests, coverage, linting, and Docker image build.

## Docker

```bash
docker build -t ai-support-ticket-platform .
docker run -p 8000:8000 --env-file .env ai-support-ticket-platform
```

## Render Deployment

1. Create a Render PostgreSQL database.
2. Create a Render Web Service from this GitHub repo.
3. Use Docker as the runtime.
4. Set environment variables:

```text
DATABASE_URL=<Render PostgreSQL internal URL>
ENVIRONMENT=production
API_KEY=<strong secret>
USE_LLM=true
OPENAI_API_KEY=<your OpenAI key>
LLM_MODEL=gpt-4o-mini
KNOWLEDGE_BASE_PATH=knowledge_base
```

5. Deploy. The app initializes tables on startup.

See [docs/demo-script.md](docs/demo-script.md) for an interview walkthrough and [docs/architecture.md](docs/architecture.md) for design notes.

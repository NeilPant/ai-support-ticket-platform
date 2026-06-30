# AI-Heavy Professional Upgrade Plan

## Summary
Upgrade the current FastAPI/LangGraph support-ticket backend into a polished, AI-heavy portfolio project that demonstrates real agent orchestration, RAG, structured LLM outputs, evaluation, observability, persistence, CI, and Render deployment. The project will remain demo-friendly: it should work without paid calls in fallback mode, but its primary professional path will use OpenAI + LangChain + LangGraph.

## Key Changes

### AI Workflow
- Replace keyword-only classification with a hybrid workflow:
  - deterministic fallback for no-key demos
  - OpenAI structured-output classifier for category, priority, sentiment, urgency, risk signals, and confidence
- Expand LangGraph into a more impressive multi-node agent graph:
  - `intake_validator`
  - `classifier`
  - `rag_retriever`
  - `resolution_planner`
  - `response_writer`
  - `escalation_decider`
  - `quality_guardrail`
  - `audit_logger`
- Add structured workflow state with:
  - `classification`
  - `retrieved_context`
  - `resolution_plan`
  - `drafted_response`
  - `escalation_decision`
  - `quality_review`
  - `trace_id`
  - `token_usage` where available
- Add deterministic fallback implementations for every LLM node so tests and demos never depend on an API key.

### RAG Knowledge Base
- Add a local markdown support-docs corpus under a repo directory such as `knowledge_base/`.
- Add an ingestion module that chunks local docs and stores searchable chunks.
- Use a lightweight local vector store for portfolio practicality:
  - default: Chroma or FAISS
  - fallback: lexical search if vector dependencies or API keys are unavailable
- Add APIs:
  - `POST /knowledge/reindex`
  - `GET /knowledge/documents`
  - `GET /knowledge/search?query=...`
- Make ticket resolution use retrieved context rather than hardcoded snippets.

### API + Data Model
- Move from direct module-level service initialization to FastAPI dependency injection.
- Keep SQLite for local development, but make the repository database URL configurable for Render/PostgreSQL.
- Add SQLAlchemy or SQLModel for professional persistence instead of manual SQLite queries.
- Add database tables/models for:
  - tickets
  - workflow runs
  - workflow steps
  - knowledge documents
  - retrieved chunks
  - audit events
- Add ticket lifecycle APIs:
  - `PATCH /tickets/{ticket_id}` for status/manual updates
  - `POST /tickets/{ticket_id}/workflow-runs`
  - `GET /tickets/{ticket_id}/workflow-runs`
  - `GET /workflow-runs/{run_id}`
- Add pagination and filters to `GET /tickets`:
  - status
  - category
  - priority
  - escalation required
  - created date range
  - search query

### Professional Backend Features
- Add API-key authentication for protected admin/demo endpoints.
- Add request IDs and structured JSON logging.
- Add centralized error handling with consistent error response shapes.
- Add rate-limit-friendly LLM wrapper with timeout, retry, fallback, and clear provider error handling.
- Add settings validation through `.env.example`.
- Add app startup checks:
  - database reachable
  - knowledge index available
  - LLM mode configured or fallback active
- Add a `/health` and `/readiness` split:
  - `/health` confirms app is alive
  - `/readiness` confirms DB and knowledge index are usable

### Demo + Presentation
- Add a polished README with:
  - architecture diagram
  - LangGraph workflow diagram
  - screenshots or sample responses
  - Render deployment steps
  - local setup
  - LLM and no-LLM modes
  - demo script for interviews
- Add a `docs/demo-script.md` with a 3-minute walkthrough:
  - seed tickets
  - run workflow
  - inspect retrieved context
  - view escalation reasoning
  - show analytics
- Add `examples/` requests for:
  - ticket creation
  - knowledge search
  - workflow execution
  - analytics
  - protected admin endpoints
- Optional but recommended after backend polish: add a small Streamlit dashboard or static FastAPI-served demo page to visualize tickets, workflow runs, retrieved context, and escalation decisions.

## Testing And Quality

### Tests
- Expand pytest coverage from basic endpoint tests to:
  - API validation tests
  - repository tests
  - service tests
  - LangGraph node tests
  - full workflow integration tests
  - RAG ingestion/search tests
  - no-LLM fallback tests
  - mocked OpenAI structured-output tests
  - auth tests
  - error-path tests
- Add test fixtures with isolated temporary databases and deterministic knowledge docs.
- Add snapshot-style assertions for important response shapes.

### Tooling
- Add `pyproject.toml` with:
  - Ruff linting
  - Ruff formatting
  - Pytest config
  - coverage config
  - optional mypy configuration
- Add GitHub Actions CI:
  - install dependencies
  - run lint
  - run tests
  - run coverage
  - build Docker image
- Target at least 80 percent meaningful test coverage.

### Acceptance Criteria
- `pytest` passes locally and in GitHub Actions.
- App runs locally with no API key using deterministic fallbacks.
- App runs with OpenAI enabled using `.env`.
- `POST /demo/seed` creates realistic tickets.
- `POST /tickets/{ticket_id}/workflow-runs` produces a persisted, inspectable workflow run.
- RAG retrieval returns relevant chunks from local markdown docs.
- README lets a recruiter run the project in under 10 minutes.
- Render deployment works from Docker with environment variables.

## Deployment Plan
- Keep Docker as the main deployment artifact.
- Add Render deployment instructions:
  - Web Service from GitHub repo
  - Docker environment
  - PostgreSQL add-on
  - environment variables from `.env.example`
- Add production settings:
  - `DATABASE_URL`
  - `OPENAI_API_KEY`
  - `USE_LLM=true`
  - `API_KEY`
  - `ENVIRONMENT=production`
- Add a startup migration/init command so the database schema is ready on deploy.
- Keep local SQLite as the default for easy development.

## Assumptions
- Primary upgrade direction is AI-heavy.
- LLM provider is OpenAI.
- RAG source is a local markdown support-docs corpus committed to the repo.
- Deployment target is Docker + Render.
- The current public GitHub repo remains the project home.
- Resume and LaTeX files stay ignored and out of the public repo.
- The project should prioritize impressive, working portfolio value over adding a large frontend first.

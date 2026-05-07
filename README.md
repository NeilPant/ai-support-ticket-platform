# AI Support Ticket Resolution Platform

A portfolio-ready FastAPI backend that demonstrates REST API design, LangGraph agent orchestration, LangChain-ready LLM integration, SQLite persistence, testing, and cloud-friendly packaging.

The platform accepts customer support tickets, runs an AI workflow, drafts a response, decides whether to escalate, and exposes analytics for the support queue.

## Why This Project Stands Out

- Clean Python package structure with API, service, repository, model, and workflow layers
- FastAPI REST endpoints with automatic Swagger docs
- LangGraph workflow composed of focused agent nodes
- Deterministic demo mode that works without paid API keys
- Optional LangChain/OpenAI response generation
- SQLite persistence instead of in-memory state
- Pytest coverage for API behavior and workflow outputs
- Dockerfile, `.env.example`, API examples, and architecture notes

## Workflow

```text
classifier
  -> knowledge_retriever
  -> resolution_writer
  -> escalation_router
  -> quality_checker
```

The workflow returns:

- ticket category and priority
- retrieved support guidance
- drafted customer response
- escalation decision and reason
- risk signals
- recommended support actions
- quality score

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

Seed realistic sample tickets:

```bash
curl -X POST http://127.0.0.1:8000/demo/seed
```

View analytics:

```bash
curl http://127.0.0.1:8000/analytics/summary
```

Inspect the workflow:

```bash
curl http://127.0.0.1:8000/workflow/definition
```

Create your own ticket:

```bash
curl -X POST http://127.0.0.1:8000/tickets ^
  -H "Content-Type: application/json" ^
  -d "{\"customer_email\":\"alex@example.com\",\"subject\":\"Production API returns 500\",\"description\":\"Our production API endpoint returns 500 errors and customers are blocked.\"}"
```

Then resolve it:

```bash
curl -X POST http://127.0.0.1:8000/tickets/{ticket_id}/resolve
```

## Endpoints

```text
GET  /health
POST /tickets
GET  /tickets
GET  /tickets/{ticket_id}
POST /tickets/{ticket_id}/analyze
POST /tickets/{ticket_id}/resolve
GET  /tickets/{ticket_id}/workflow-status
GET  /workflow/definition
POST /demo/seed
GET  /analytics/summary
```

## Optional LLM Mode

The app works without an LLM by default. To enable LLM drafting:

```bash
pip install langchain-openai
$env:OPENAI_API_KEY="your-key"
$env:USE_LLM="true"
uvicorn app.main:app --reload
```

If the provider package or API call fails, the app falls back to deterministic response drafting so demos keep working.

## Run Tests

```bash
pytest
```

## Docker

```bash
docker build -t ai-support-ticket-platform .
docker run -p 8000:8000 --env-file .env ai-support-ticket-platform
```

## Cloud Deployment Notes

This project can be deployed as a container on AWS ECS, Azure Container Apps, Google Cloud Run, or a VM. For a production deployment, replace local SQLite with managed PostgreSQL and store secrets in the cloud provider's secret manager.

See [docs/architecture.md](docs/architecture.md) for the system design.

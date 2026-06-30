# 3-Minute Demo Script

## 1. Start the API

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

## 2. Index The Knowledge Base

Call `POST /knowledge/reindex` with:

```text
X-API-Key: dev-api-key
```

This indexes the local markdown support playbooks.

## 3. Seed Demo Tickets

Call `POST /demo/seed` with the same API key. The app creates realistic billing, API, and authentication tickets and runs the full LangGraph workflow.

## 4. Inspect A Workflow Run

Open one result from `GET /tickets/{ticket_id}/workflow-runs`.

Point out:

- classification and confidence
- retrieved RAG context
- resolution plan
- escalation decision
- quality guardrail score
- trace ID and step history

## 5. Show Analytics

Call `GET /analytics/summary` and explain how escalations and categories are calculated from persisted workflow runs.

from __future__ import annotations

from typing import TypedDict
from uuid import uuid4

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph

from app.models.ticket import (
    ClassificationResult,
    EscalationDecision,
    QualityReview,
    ResolutionPlan,
    RetrievedContext,
    Ticket,
    TicketCategory,
    TicketPriority,
    TicketStatus,
    TokenUsage,
    WorkflowResult,
)
from app.services.knowledge_service import KnowledgeService
from app.services.llm_service import LLMService


class SupportWorkflowState(TypedDict, total=False):
    ticket: Ticket
    trace_id: str
    classification: ClassificationResult
    retrieved_context: list[RetrievedContext]
    resolution_plan: ResolutionPlan
    drafted_response: str
    escalation_decision: EscalationDecision
    quality_review: QualityReview
    token_usage: TokenUsage
    workflow_steps: list[str]


class SupportTicketWorkflow:
    def __init__(self, knowledge_service: KnowledgeService, llm_service: LLMService | None = None) -> None:
        self.knowledge_service = knowledge_service
        self.llm_service = llm_service or LLMService()
        self._graph = self._build_graph()

    def run(self, ticket: Ticket) -> WorkflowResult:
        self.knowledge_service.ensure_indexed()
        initial_state: SupportWorkflowState = {
            "ticket": ticket,
            "trace_id": str(uuid4()),
            "workflow_steps": [],
            "token_usage": TokenUsage(),
        }
        state = self._graph.invoke(initial_state)
        classification = state["classification"]
        escalation = state["escalation_decision"]
        quality = state["quality_review"]
        status = TicketStatus.escalated if escalation.required else TicketStatus.resolved
        return WorkflowResult(
            ticket_id=ticket.id,
            trace_id=state["trace_id"],
            status=status,
            category=classification.category,
            priority=classification.priority,
            classification=classification,
            retrieved_context=state["retrieved_context"],
            knowledge_snippets=[item.content for item in state["retrieved_context"]],
            resolution_plan=state["resolution_plan"],
            drafted_response=state["drafted_response"],
            escalation_decision=escalation,
            escalation_required=escalation.required,
            escalation_reason=escalation.reason,
            quality_review=quality,
            quality_score=quality.score,
            risk_signals=classification.risk_signals,
            recommended_actions=state["resolution_plan"].next_steps,
            workflow_steps=state["workflow_steps"],
            token_usage=state["token_usage"],
        )

    def analyze(self, ticket: Ticket) -> WorkflowResult:
        self.knowledge_service.ensure_indexed()
        state: SupportWorkflowState = {
            "ticket": ticket,
            "trace_id": str(uuid4()),
            "workflow_steps": [],
            "token_usage": TokenUsage(),
        }
        state = self._intake_validator(state)
        state = self._classifier(state)
        state = self._rag_retriever(state)
        classification = state["classification"]
        return WorkflowResult(
            ticket_id=ticket.id,
            trace_id=state["trace_id"],
            status=TicketStatus.analyzed,
            category=classification.category,
            priority=classification.priority,
            classification=classification,
            retrieved_context=state["retrieved_context"],
            knowledge_snippets=[item.content for item in state["retrieved_context"]],
            risk_signals=classification.risk_signals,
            workflow_steps=state["workflow_steps"],
        )

    def describe(self) -> dict[str, object]:
        nodes = [
            "intake_validator",
            "classifier",
            "rag_retriever",
            "resolution_planner",
            "response_writer",
            "escalation_decider",
            "quality_guardrail",
            "audit_logger",
        ]
        return {
            "name": "ai_support_ticket_resolution_graph",
            "nodes": nodes,
            "edges": list(zip(nodes, nodes[1:], strict=False)),
        }

    def _build_graph(self):
        graph = StateGraph(SupportWorkflowState)
        graph.add_node("intake_validator", self._intake_validator)
        graph.add_node("classifier", self._classifier)
        graph.add_node("rag_retriever", self._rag_retriever)
        graph.add_node("resolution_planner", self._resolution_planner)
        graph.add_node("response_writer", self._response_writer)
        graph.add_node("escalation_decider", self._escalation_decider)
        graph.add_node("quality_guardrail", self._quality_guardrail)
        graph.add_node("audit_logger", self._audit_logger)

        graph.set_entry_point("intake_validator")
        graph.add_edge("intake_validator", "classifier")
        graph.add_edge("classifier", "rag_retriever")
        graph.add_edge("rag_retriever", "resolution_planner")
        graph.add_edge("resolution_planner", "response_writer")
        graph.add_edge("response_writer", "escalation_decider")
        graph.add_edge("escalation_decider", "quality_guardrail")
        graph.add_edge("quality_guardrail", "audit_logger")
        graph.add_edge("audit_logger", END)
        return graph.compile()

    def _intake_validator(self, state: SupportWorkflowState) -> SupportWorkflowState:
        ticket = state["ticket"]
        if len(ticket.description.strip()) < 10:
            raise ValueError("Ticket description is too short for workflow processing.")
        return self._append_step(state, "intake_validator")

    def _classifier(self, state: SupportWorkflowState) -> SupportWorkflowState:
        ticket = state["ticket"]
        fallback = self._fallback_classification(ticket)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Classify customer support tickets. Return structured fields only.",
                ),
                (
                    "human",
                    "Subject: {subject}\nDescription: {description}",
                ),
            ]
        )
        classification, _usage = self.llm_service.structured(
            prompt,
            ClassificationResult,
            {"subject": ticket.subject, "description": ticket.description},
            fallback,
        )
        return self._append_step({**state, "classification": classification}, "classifier")

    def _rag_retriever(self, state: SupportWorkflowState) -> SupportWorkflowState:
        ticket = state["ticket"]
        query = f"{ticket.subject} {ticket.description}"
        retrieved = self.knowledge_service.search(query, limit=4).results
        return self._append_step({**state, "retrieved_context": retrieved}, "rag_retriever")

    def _resolution_planner(self, state: SupportWorkflowState) -> SupportWorkflowState:
        classification = state["classification"]
        context = state["retrieved_context"]
        fallback = ResolutionPlan(
            summary=f"Handle as a {classification.priority.value} {classification.category.value} support case.",
            next_steps=[
                "Acknowledge the customer and summarize the issue.",
                "Use the retrieved support playbook guidance before proposing a fix.",
                "Collect missing diagnostic details if the ticket lacks request IDs or payment references.",
            ],
            customer_questions=self._customer_questions(classification),
            internal_notes=[f"Risk signals: {', '.join(classification.risk_signals) or 'none detected'}"],
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "Create a concise support resolution plan from classification and retrieved context."),
                (
                    "human",
                    "Classification: {classification}\nContext: {context}",
                ),
            ]
        )
        plan, _usage = self.llm_service.structured(
            prompt,
            ResolutionPlan,
            {
                "classification": classification.model_dump_json(),
                "context": "\n\n".join(item.content for item in context),
            },
            fallback,
        )
        return self._append_step({**state, "resolution_plan": plan}, "resolution_planner")

    def _response_writer(self, state: SupportWorkflowState) -> SupportWorkflowState:
        ticket = state["ticket"]
        plan = state["resolution_plan"]
        context = state["retrieved_context"]
        fallback = (
            f"Thanks for contacting support. We reviewed your ticket, '{ticket.subject}', "
            f"and identified this as a {state['classification'].priority.value} "
            f"{state['classification'].category.value.replace('_', ' ')} issue. "
            f"{plan.summary} {context[0].content if context else ''} "
            "Please share any missing details requested above so we can continue quickly."
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "Draft a helpful, safe customer support response. Do not invent facts."),
                (
                    "human",
                    "Ticket: {ticket}\nPlan: {plan}\nContext: {context}",
                ),
            ]
        )
        response, _usage = self.llm_service.text(
            prompt,
            {
                "ticket": ticket.model_dump_json(),
                "plan": plan.model_dump_json(),
                "context": "\n\n".join(item.content for item in context),
            },
            fallback,
        )
        return self._append_step({**state, "drafted_response": response}, "response_writer")

    def _escalation_decider(self, state: SupportWorkflowState) -> SupportWorkflowState:
        classification = state["classification"]
        signals = set(classification.risk_signals)
        required = (
            classification.priority == TicketPriority.urgent
            or "production impact" in signals
            or "payment sensitivity" in signals
        )
        target_team = None
        if required and classification.category == TicketCategory.api_error:
            target_team = "on-call engineering"
        elif required and classification.category == TicketCategory.billing:
            target_team = "billing operations"
        reason = None
        if required:
            reason = "High-impact risk signals require human review before final closure."
        decision = EscalationDecision(required=required, reason=reason, target_team=target_team)
        return self._append_step({**state, "escalation_decision": decision}, "escalation_decider")

    def _quality_guardrail(self, state: SupportWorkflowState) -> SupportWorkflowState:
        response = state["drafted_response"].lower()
        issues = []
        if len(response.split()) < 35:
            issues.append("Response is too short.")
        if "thanks" not in response and "sorry" not in response:
            issues.append("Response lacks acknowledgement.")
        if "cvv" in response or "password" in response and "do not" not in response:
            issues.append("Response may request sensitive credentials.")
        score = round(max(0, 1 - (len(issues) * 0.25)), 2)
        review = QualityReview(score=score, passed=score >= 0.75, issues=issues)
        return self._append_step({**state, "quality_review": review}, "quality_guardrail")

    def _audit_logger(self, state: SupportWorkflowState) -> SupportWorkflowState:
        return self._append_step(state, "audit_logger")

    def _fallback_classification(self, ticket: Ticket) -> ClassificationResult:
        text = f"{ticket.subject} {ticket.description}".lower()
        category = TicketCategory.general
        if any(term in text for term in ("payment", "invoice", "refund", "charged", "billing", "debited")):
            category = TicketCategory.billing
        elif any(term in text for term in ("password", "login", "mfa", "reset", "account locked")):
            category = TicketCategory.authentication
        elif any(term in text for term in ("api", "500", "timeout", "endpoint", "request id")):
            category = TicketCategory.api_error
        elif any(term in text for term in ("slow", "latency", "performance", "lag")):
            category = TicketCategory.performance

        priority = TicketPriority.medium
        if any(term in text for term in ("production", "outage", "down", "urgent", "blocked")):
            priority = TicketPriority.urgent
        elif any(term in text for term in ("failed", "cannot", "error", "locked", "debited")):
            priority = TicketPriority.high
        elif any(term in text for term in ("question", "how do i", "feature request")):
            priority = TicketPriority.low

        signals = []
        signal_terms = {
            "production impact": ("production", "outage", "down", "blocked"),
            "payment sensitivity": ("debited", "charged", "refund", "invoice"),
            "server-side failure": ("500", "timeout", "api error"),
            "account access": ("locked", "mfa", "password", "login"),
        }
        for label, terms in signal_terms.items():
            if any(term in text for term in terms):
                signals.append(label)
        urgency = {"low": 0.2, "medium": 0.45, "high": 0.7, "urgent": 0.95}[priority.value]
        sentiment = "frustrated" if any(term in text for term in ("failed", "cannot", "blocked")) else "neutral"
        return ClassificationResult(
            category=category,
            priority=priority,
            sentiment=sentiment,
            urgency_score=urgency,
            confidence=0.78,
            risk_signals=signals,
        )

    def _customer_questions(self, classification: ClassificationResult) -> list[str]:
        if classification.category == TicketCategory.api_error:
            return ["Can you share the request ID, endpoint, timestamp, and response code?"]
        if classification.category == TicketCategory.billing:
            return ["Can you share the order ID and payment attempt timestamp?"]
        if classification.category == TicketCategory.authentication:
            return ["Have you requested a new reset link in the last 30 minutes?"]
        return ["Can you share one example with timestamp and expected outcome?"]

    def _append_step(self, state: SupportWorkflowState, step: str) -> SupportWorkflowState:
        return {**state, "workflow_steps": [*state.get("workflow_steps", []), step]}

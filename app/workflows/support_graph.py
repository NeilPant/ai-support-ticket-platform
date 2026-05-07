from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph

from app.core.config import get_settings
from app.models.ticket import Ticket, TicketCategory, TicketPriority, TicketStatus, WorkflowResult
from app.workflows.knowledge_base import KNOWLEDGE_BASE


class SupportWorkflowState(TypedDict, total=False):
    ticket: Ticket
    category: TicketCategory
    priority: TicketPriority
    knowledge_snippets: list[str]
    drafted_response: str
    escalation_required: bool
    escalation_reason: str | None
    quality_score: float
    risk_signals: list[str]
    recommended_actions: list[str]
    workflow_steps: list[str]


class SupportTicketWorkflow:
    """LangGraph workflow that coordinates ticket resolution agents."""

    def __init__(self) -> None:
        self._graph = self._build_graph()

    def run(self, ticket: Ticket) -> WorkflowResult:
        initial_state: SupportWorkflowState = {"ticket": ticket, "workflow_steps": []}
        final_state = self._graph.invoke(initial_state)

        return WorkflowResult(
            ticket_id=ticket.id,
            status=TicketStatus.escalated if final_state["escalation_required"] else TicketStatus.resolved,
            category=final_state["category"],
            priority=final_state["priority"],
            knowledge_snippets=final_state["knowledge_snippets"],
            drafted_response=final_state["drafted_response"],
            escalation_required=final_state["escalation_required"],
            escalation_reason=final_state["escalation_reason"],
            quality_score=final_state["quality_score"],
            risk_signals=final_state["risk_signals"],
            recommended_actions=final_state["recommended_actions"],
            workflow_steps=final_state["workflow_steps"],
        )

    def analyze(self, ticket: Ticket) -> WorkflowResult:
        state = self._classify({"ticket": ticket, "workflow_steps": []})
        state = self._retrieve_knowledge(state)

        return WorkflowResult(
            ticket_id=ticket.id,
            status=TicketStatus.analyzed,
            category=state["category"],
            priority=state["priority"],
            knowledge_snippets=state["knowledge_snippets"],
            risk_signals=self._detect_risk_signals(ticket),
            recommended_actions=self._recommended_actions(state),
            workflow_steps=state["workflow_steps"],
        )

    def describe(self) -> dict[str, object]:
        return {
            "name": "support_ticket_resolution_graph",
            "nodes": [
                "classifier",
                "knowledge_retriever",
                "resolution_writer",
                "escalation_router",
                "quality_checker",
            ],
            "edges": [
                ("classifier", "knowledge_retriever"),
                ("knowledge_retriever", "resolution_writer"),
                ("resolution_writer", "escalation_router"),
                ("escalation_router", "quality_checker"),
            ],
        }

    def _build_graph(self):
        graph = StateGraph(SupportWorkflowState)
        graph.add_node("classifier", self._classify)
        graph.add_node("retriever", self._retrieve_knowledge)
        graph.add_node("resolution_writer", self._draft_response)
        graph.add_node("escalation_router", self._route_escalation)
        graph.add_node("quality_checker", self._quality_check)

        graph.set_entry_point("classifier")
        graph.add_edge("classifier", "retriever")
        graph.add_edge("retriever", "resolution_writer")
        graph.add_edge("resolution_writer", "escalation_router")
        graph.add_edge("escalation_router", "quality_checker")
        graph.add_edge("quality_checker", END)
        return graph.compile()

    def _classify(self, state: SupportWorkflowState) -> SupportWorkflowState:
        ticket = state["ticket"]
        text = f"{ticket.subject} {ticket.description}".lower()

        category = TicketCategory.general
        if any(term in text for term in ("payment", "invoice", "refund", "charged", "billing")):
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
        elif any(term in text for term in ("failed", "cannot", "error", "locked")):
            priority = TicketPriority.high
        elif any(term in text for term in ("question", "how do i", "feature request")):
            priority = TicketPriority.low

        return {
            **state,
            "category": category,
            "priority": priority,
            "workflow_steps": [*state.get("workflow_steps", []), "classifier"],
        }

    def _retrieve_knowledge(self, state: SupportWorkflowState) -> SupportWorkflowState:
        snippets = KNOWLEDGE_BASE[state["category"]]
        return {
            **state,
            "knowledge_snippets": snippets,
            "workflow_steps": [*state.get("workflow_steps", []), "knowledge_retriever"],
        }

    def _draft_response(self, state: SupportWorkflowState) -> SupportWorkflowState:
        settings = get_settings()
        if settings.use_llm and settings.openai_api_key:
            response = self._draft_with_llm(state)
        else:
            response = self._draft_deterministic_response(state)

        return {
            **state,
            "drafted_response": response,
            "workflow_steps": [*state.get("workflow_steps", []), "resolution_writer"],
        }

    def _route_escalation(self, state: SupportWorkflowState) -> SupportWorkflowState:
        category = state["category"]
        priority = state["priority"]
        text = f"{state['ticket'].subject} {state['ticket'].description}".lower()

        escalation_required = priority == TicketPriority.urgent or (
            category in {TicketCategory.billing, TicketCategory.api_error}
            and any(term in text for term in ("debited", "production", "500", "outage"))
        )

        reason = None
        if escalation_required:
            reason = "The ticket involves a high-impact or sensitive issue that needs human review."

        return {
            **state,
            "escalation_required": escalation_required,
            "escalation_reason": reason,
            "risk_signals": self._detect_risk_signals(state["ticket"]),
            "recommended_actions": self._recommended_actions(state),
            "workflow_steps": [*state.get("workflow_steps", []), "escalation_router"],
        }

    def _quality_check(self, state: SupportWorkflowState) -> SupportWorkflowState:
        response = state["drafted_response"]
        checks = [
            "sorry" in response.lower() or "thanks" in response.lower(),
            state["category"].value.replace("_", " ") in response.lower(),
            len(response.split()) >= 35,
        ]
        quality_score = round(sum(checks) / len(checks), 2)

        return {
            **state,
            "quality_score": quality_score,
            "workflow_steps": [*state.get("workflow_steps", []), "quality_checker"],
        }

    def _draft_deterministic_response(self, state: SupportWorkflowState) -> str:
        ticket = state["ticket"]
        snippets = state["knowledge_snippets"]
        category = state["category"].value.replace("_", " ")

        return (
            f"Thanks for contacting support about this {category} issue. "
            f"We reviewed your ticket, '{ticket.subject}', and identified the next best steps. "
            f"{snippets[0]} {snippets[1] if len(snippets) > 1 else ''} "
            "Please share any missing details requested above so we can continue troubleshooting quickly."
        )

    def _detect_risk_signals(self, ticket: Ticket) -> list[str]:
        text = f"{ticket.subject} {ticket.description}".lower()
        signals: list[str] = []
        signal_terms = {
            "production impact": ("production", "outage", "down", "blocked"),
            "payment sensitivity": ("debited", "charged", "refund", "invoice"),
            "server-side failure": ("500", "timeout", "api error"),
            "account access": ("locked", "mfa", "password", "login"),
        }
        for label, terms in signal_terms.items():
            if any(term in text for term in terms):
                signals.append(label)
        return signals

    def _recommended_actions(self, state: SupportWorkflowState) -> list[str]:
        category = state["category"]
        priority = state["priority"]
        actions = [
            "Send the drafted response to acknowledge the issue.",
            "Attach the retrieved knowledge-base guidance to the internal ticket.",
        ]
        if category == TicketCategory.api_error:
            actions.append("Collect request ID, endpoint, timestamp, and response code.")
        if category == TicketCategory.billing:
            actions.append("Verify payment provider status before discussing refunds.")
        if priority in {TicketPriority.high, TicketPriority.urgent}:
            actions.append("Assign the ticket to the on-call support queue.")
        return actions

    def _draft_with_llm(self, state: SupportWorkflowState) -> str:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            return self._draft_deterministic_response(state)

        try:
            settings = get_settings()
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a concise support specialist. Draft a helpful response using the provided guidance.",
                    ),
                    (
                        "human",
                        "Subject: {subject}\nDescription: {description}\nCategory: {category}\nGuidance: {guidance}",
                    ),
                ]
            )
            model = ChatOpenAI(model=settings.llm_model, api_key=settings.openai_api_key)
            chain = prompt | model
            result = chain.invoke(
                {
                    "subject": state["ticket"].subject,
                    "description": state["ticket"].description,
                    "category": state["category"].value,
                    "guidance": "\n".join(state["knowledge_snippets"]),
                }
            )
            return str(result.content)
        except Exception:
            return self._draft_deterministic_response(state)

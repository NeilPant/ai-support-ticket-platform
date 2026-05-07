from app.models.ticket import TicketCategory


KNOWLEDGE_BASE: dict[TicketCategory, list[str]] = {
    TicketCategory.billing: [
        "Check whether the payment provider returned a decline code or a network timeout.",
        "Ask the customer to confirm card details only through the secure payment page.",
        "If money was debited but the order failed, escalate to billing operations.",
    ],
    TicketCategory.authentication: [
        "Password reset links expire after 30 minutes.",
        "Account lockouts clear automatically after 15 minutes unless suspicious activity is detected.",
        "For MFA issues, verify backup code availability before disabling a factor.",
    ],
    TicketCategory.api_error: [
        "Collect request ID, timestamp, endpoint, status code, and payload shape.",
        "HTTP 500 responses should be correlated with application logs before replying.",
        "Repeated production API failures require engineering escalation.",
    ],
    TicketCategory.performance: [
        "Ask for region, endpoint, latency samples, and whether the issue is intermittent.",
        "Check the service status page and recent deployments before suggesting client-side changes.",
    ],
    TicketCategory.general: [
        "Acknowledge the issue, summarize the user's request, and ask one focused follow-up if needed.",
    ],
}


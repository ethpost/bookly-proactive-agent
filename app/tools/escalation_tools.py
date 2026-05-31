import uuid

def create_escalation_ticket(order_id: str, conversation_summary: str) -> dict:
    ticket_id = str(uuid.uuid4())
    return {
        "order_id": order_id,
        "ticket_id": ticket_id,
        "status": "created",
        "priority": "high",
        "summary": (
            "Escalation created for delayed order, customer requested human support."
        ),
        "conversation_summary": conversation_summary,
    }

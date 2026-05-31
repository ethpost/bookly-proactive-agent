from app.services.openai_client import OpenAIClient
from app.services.trace import new_trace
from app.tools.escalation_tools import create_escalation_ticket
from app.models import ConversationState


def handle_escalation_intent(state: ConversationState) -> tuple[str, list[dict]]:
    traces = []
    ticket = create_escalation_ticket(state.order_id, state.conversation_summary)

    traces.append(
        new_trace(
            type="action_completed",
            agent="EscalationAgent",
            title="Escalation ticket created",
            summary="Created a human support escalation ticket for the customer issue.",
            outputs=ticket,
        )
    )

    client = OpenAIClient()
    response_prompt = [
        {
            "role": "system",
            "content": (
                "You are the Bookly EscalationAgent. Inform the customer that a human specialist has been engaged. "
                "Be reassuring, clear, and avoid mentioning any internal ticket details."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Order ID: {state.order_id}\n"
                f"Issue summary: {state.conversation_summary}\n"
                "Provide a helpful message telling the customer that a specialist will review their case and they do not need to repeat details."
            ),
        },
    ]
    response = client.chat(response_prompt, temperature=0.5)

    state.escalation_created = True
    state.completed_actions.append("escalation_created")
    state.active_agent = "escalation"
    state.current_intent = "request_escalation"

    traces.append(
        new_trace(
            type="customer_response_generated",
            agent="EscalationAgent",
            title="Escalation response drafted",
            summary="Generated a customer-facing escalation confirmation.",
            outputs={"message": response},
        )
    )

    return response, [trace.dict() for trace in traces]

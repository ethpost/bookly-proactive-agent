from app.services.openai_client import OpenAIClient
from app.services.trace import new_trace
from app.tools.order_tools import get_order, get_customer_memory
from app.tools.policy_tools import get_policy
from app.models import ConversationState


def create_proactive_message(state: ConversationState) -> tuple[str, list[dict]]:
    traces = []
    order = get_order(state.order_id)
    memory = get_customer_memory(state.customer_id)
    policy = get_policy("service_recovery_policy")

    traces.append(
        new_trace(
            type="operational_event",
            agent="ProactiveAgent",
            title="Shipping delay detected",
            summary=(
                f"Order {state.order_id} slipped from {order.get('original_eta')} to "
                f"{order.get('updated_eta')} due to carrier delay."
            ),
            inputs={"order_id": state.order_id},
            outputs={"status": order.get("status")},
        )
    )

    traces.append(
        new_trace(
            type="context_retrieved",
            agent="ProactiveAgent",
            title="Order context retrieved",
            summary="Loaded the delayed order and current ETA from Bookly records.",
            outputs=order,
        )
    )

    traces.append(
        new_trace(
            type="memory_retrieved",
            agent="ProactiveAgent",
            title="Customer memory retrieved",
            summary="Customer previously indicated the order is needed for a Saturday morning birthday party.",
            outputs=memory,
        )
    )

    traces.append(
        new_trace(
            type="policy_loaded",
            agent="ProactiveAgent",
            title="Service recovery policy loaded",
            summary="Loaded Bookly policy for delayed shipments and service recovery.",
            outputs={"policy_name": policy.get("title")},
        )
    )

    traces.append(
        new_trace(
            type="supervisor_decision",
            agent="ProactiveAgent",
            title="Proactive outreach warranted",
            summary=(
                "Updated ETA misses the known need-by date, so proactive SMS outreach is required."
            ),
        )
    )

    prompt = [
        {
            "role": "system",
            "content": (
                "You are a customer support assistant for Bookly. Draft a short outbound SMS-style update "
                "for Jane Miller about a delayed birthday gift order. Use the event details, keep the tone empathetic, include details about the original order"
                "and do not mention internal systems or tools."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Order ID: {state.order_id}. Item: {order.get('item')}. "
                f"Original ETA: {order.get('original_eta')}. Updated ETA: {order.get('updated_eta')}. "
                f"Customer need-by: {state.known_need_by}. "
                "Current issue: carrier delay. Reply with a proactive message that asks the customer to respond so Bookly can help."
            ),
        },
    ]

    client = OpenAIClient()
    message = client.chat(prompt, temperature=0.4)

    traces.append(
        new_trace(
            type="customer_response_generated",
            agent="ProactiveAgent",
            title="Outbound SMS generated",
            summary="Generated the proactive customer-facing SMS using OpenAI.",
            outputs={"message": message},
        )
    )

    return message.strip(), [trace.dict() for trace in traces]

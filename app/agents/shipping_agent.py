from app.services.openai_client import OpenAIClient
from app.services.trace import new_trace
from app.tools.shipping_tools import get_tracking_status, estimate_delivery_options
from app.models import ConversationState


def handle_shipping_intent(message: str, state: ConversationState) -> tuple[str, list[dict]]:
    traces = []
    tracking = get_tracking_status(state.order_id)
    options = estimate_delivery_options(state.order_id, state.known_need_by)

    # Determine whether any available option meets the customer's need-by date
    any_on_time = any(o.get("meets_need_by") for o in options.get("options", []))
    traces.append(
        new_trace(
            type="tool_call",
            agent="ShippingAgent",
            title="get_tracking_status",
            summary="Retrieved tracking status for the delayed order.",
            inputs={"order_id": state.order_id},
            outputs=tracking,
        )
    )

    traces.append(
        new_trace(
            type="tool_call",
            agent="ShippingAgent",
            title="estimate_delivery_options",
            summary="Estimated available delivery options against the requested need-by date.",
            inputs={"order_id": state.order_id, "need_by": state.known_need_by},
            outputs=options,
        )
    )

    client = OpenAIClient()
    is_confidence_question = any(k in message.lower() for k in ("how confident", "confidence", "likely", "what are the chances", "chance", "will it arrive", "arrive by"))

    if is_confidence_question:
        user_content = (
            f"Customer message: \"{message}\"\n"
            f"Tracking status: {tracking}\n"
            f"Available options: {options}\n"
            "The customer is asking how confident the expedited replacement is to arrive by the requested date. "
            "Answer honestly about the timing and then ask whether they would like to proceed with expedited replacement, review similar on-time alternatives, request a refund, or talk to a human."
        )
    else:
        user_content = (
            f"Customer message: \"{message}\"\n"
            f"Tracking status: {tracking}\n"
            f"Available options: {options}\n"
            "Provide a single customer-facing response that explains the delay, confirms the missed need-by date if applicable, "
            "and summarizes the best available recovery or expedited delivery option."
        )

    prompt = [
        {
            "role": "system",
            "content": (
                "You are the Bookly ShippingAgent. Use the tracking and delivery option data to answer the customer's shipping inquiry. "
                "Keep the reply helpful, empathic, and specific to the customer's current request. "
                "Do not mention internal agent names or tool calls."
            ),
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]
    message_text = client.chat(prompt, temperature=0.6)

    state.active_agent = "shipping"
    state.current_intent = "delivery_feasibility"

    traces.append(
        new_trace(
            type="customer_response_generated",
            agent="ShippingAgent",
            title="Shipping response drafted",
            summary="Generated a customer-facing shipping update based on current tracking and delivery options.",
            outputs={"message": message_text},
        )
    )

    # If no option meets the need-by, offer to search for similar on-time alternatives
    if not any_on_time:
        state.pending_recommendation = True
        soft_offer = (
            f"If you'd prefer, I can recommend similar items that can arrive by {state.known_need_by}. "
            "Would you like me to look for alternatives instead of a refund?"
        )
        # Append the soft handoff prompt to the response so the customer is guided
        message_text = message_text.strip() + "\n\n" + soft_offer

        traces.append(
            new_trace(
                type="handoff",
                agent="ShippingAgent",
                title="Recommendation offered",
                summary="Offered to search for similar on-time replacement items as an alternative to refund.",
                outputs={"offer": soft_offer},
            )
        )
    return message_text, [trace.dict() for trace in traces]

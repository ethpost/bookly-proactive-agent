from app.models import ConversationState


def create_initial_state() -> ConversationState:
    return ConversationState(
        scenario_id="delayed_birthday_gift_recovery",
        customer_id="CUST-1007",
        order_id="BK-1042",
        known_need_by="Saturday morning",
        active_agent="proactive",
        current_intent=None,
        offered_options=["expedited_replacement", "refund", "escalation"],
        pending_confirmation=None,
        completed_actions=[],
        conversation_summary="",
        messages=[],
        refund_issued=False,
        expedited_replacement_created=False,
        escalation_created=False,
        preferred_channel="sms",
        order_value=34.98,
    )


def add_message(state: ConversationState, role: str, text: str) -> None:
    state.messages.append({"role": role, "text": text})
    if role == "customer":
        state.conversation_summary = (
            f"{state.conversation_summary} Customer: {text}."
        ).strip()
    else:
        state.conversation_summary = (
            f"{state.conversation_summary} Bookly: {text}."
        ).strip()


def clear_state(state: ConversationState) -> ConversationState:
    return create_initial_state()

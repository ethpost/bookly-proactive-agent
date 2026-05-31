from app.services.openai_client import OpenAIClient
from app.services.trace import new_trace
from app.tools.refund_tools import check_refund_eligibility, issue_refund, upgrade_shipping
from app.models import ConversationState


def handle_resolution_intent(message: str, state: ConversationState, decision: dict) -> tuple[str, list[dict]]:
    traces = []
    action = decision.get("next_action")
    extracted = decision.get("extracted_fields", {}) or {}
    response = ""

    client = OpenAIClient()

    if action in {"check_refund_eligibility", "request_refund_confirmation"}:
        if (
            state.pending_confirmation
            and state.pending_confirmation.get("action") == "issue_refund"
            and any(k in message.lower() for k in ("refund", "confirm", "proceed", "go ahead", "please do", "issue me a refund"))
        ):
            refund_result = issue_refund(
                state.order_id,
                state.pending_confirmation["amount"],
                state.pending_confirmation["reason"],
            )
            traces.append(
                new_trace(
                    type="tool_call",
                    agent="ResolutionAgent",
                    title="issue_refund",
                    summary="Executed the refund after explicit customer confirmation.",
                    inputs=state.pending_confirmation,
                    outputs=refund_result,
                )
            )
            response_prompt = [
                {
                    "role": "system",
                    "content": (
                        "You are the Bookly ResolutionAgent. The customer has confirmed a refund. "
                        "Confirm the refund execution and explain what happens next."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Customer message: \"{message}\"\n"
                        f"Refund result: {refund_result}\n"
                        "Provide a customer-facing confirmation message."
                    ),
                },
            ]
            response = client.chat(response_prompt, temperature=0.4)
            state.refund_issued = True
            state.completed_actions.append("refund_issued")
            state.pending_confirmation = None
            traces.append(
                new_trace(
                    type="customer_response_generated",
                    agent="ResolutionAgent",
                    title="Resolution response drafted",
                    summary="Generated a customer-facing response for the resolution path.",
                    outputs={"message": response},
                )
            )
            state.active_agent = "resolution"
            state.current_intent = "request_refund"
            return response, [trace.dict() for trace in traces]

        eligibility = check_refund_eligibility(
            state.order_id, "delivery delay", state.known_need_by
        )
        traces.append(
            new_trace(
                type="tool_call",
                agent="ResolutionAgent",
                title="check_refund_eligibility",
                summary="Verified refund eligibility against Bookly refund policy.",
                inputs={"order_id": state.order_id, "need_by": state.known_need_by},
                outputs=eligibility,
            )
        )
        if eligibility["eligible"]:
            response_prompt = [
                {
                    "role": "system",
                    "content": (
                        "You are the Bookly ResolutionAgent. The customer is asking about refunds or recovery options for a delayed order. "
                        "Give a clear, empathetic response that references the refund eligibility details and asks the customer to confirm the refund if appropriate."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Customer message: \"{message}\"\n"
                        f"Refund eligibility: {eligibility}\n"
                        "If eligible, ask the customer to confirm the refund request in a friendly but direct way."
                    ),
                },
            ]
            response = client.chat(response_prompt, temperature=0.6)
            state.pending_confirmation = {
                "action": "issue_refund",
                "amount": eligibility["refund_amount"],
                "reason": eligibility["reason"],
            }
        else:
            response_prompt = [
                {
                    "role": "system",
                    "content": (
                        "You are the Bookly ResolutionAgent. The customer is asking about refunds for a delayed order. "
                        "Explain why a refund is not eligible and offer alternative recovery options clearly and compassionately."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Customer message: \"{message}\"\n"
                        f"Refund eligibility: {eligibility}\n"
                        "Provide a response that explains this outcome and suggests next steps."
                    ),
                },
            ]
            response = client.chat(response_prompt, temperature=0.5)

    elif action in {"issue_refund", "confirm_refund"}:
        if state.pending_confirmation and state.pending_confirmation.get("action") == "issue_refund":
            refund_result = issue_refund(
                state.order_id,
                state.pending_confirmation["amount"],
                state.pending_confirmation["reason"],
            )
            traces.append(
                new_trace(
                    type="tool_call",
                    agent="ResolutionAgent",
                    title="issue_refund",
                    summary="Executed the refund after explicit customer confirmation.",
                    inputs=state.pending_confirmation,
                    outputs=refund_result,
                )
            )
            response_prompt = [
                {
                    "role": "system",
                    "content": (
                        "You are the Bookly ResolutionAgent. The customer has confirmed a refund. "
                        "Confirm the refund execution and explain what happens next."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Customer message: \"{message}\"\n"
                        f"Refund result: {refund_result}\n"
                        "Provide a customer-facing confirmation message."
                    ),
                },
            ]
            response = client.chat(response_prompt, temperature=0.4)
            state.refund_issued = True
            state.completed_actions.append("refund_issued")
            state.pending_confirmation = None
        else:
            response_prompt = [
                {
                    "role": "system",
                    "content": (
                        "You are the Bookly ResolutionAgent. Ask for explicit refund confirmation in a polite and clear manner."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Customer message: \"{message}\"\n"
                        "Ask the customer to confirm if they want the refund to proceed."
                    ),
                },
            ]
            response = client.chat(response_prompt, temperature=0.5)
            state.pending_confirmation = {
                "action": "issue_refund",
                "amount": 34.98,
                "reason": "Delivery delay misses stated need-by date.",
            }

    elif action == "upgrade_shipping" or action == "offer_expedited_replacement":
        if state.pending_confirmation and state.pending_confirmation.get("action") == "upgrade_shipping":
            shipping_result = upgrade_shipping(state.order_id, "expedited_replacement")
            traces.append(
                new_trace(
                    type="tool_call",
                    agent="ResolutionAgent",
                    title="upgrade_shipping",
                    summary="Created a free expedited replacement shipment for the delayed order.",
                    inputs={"order_id": state.order_id, "service_level": "expedited_replacement"},
                    outputs=shipping_result,
                )
            )
            response_prompt = [
                {
                    "role": "system",
                    "content": (
                        "You are the Bookly ResolutionAgent. The customer has confirmed a refund or expedited replacement. "
                        "Confirm the shipping update and explain what happens next."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Customer message: \"{message}\"\n"
                        f"Shipping update: {shipping_result}\n"
                        "Provide a friendly confirmation that the expedited replacement is arranged."
                    ),
                },
            ]
            response = client.chat(response_prompt, temperature=0.5)
            state.expedited_replacement_created = True
            state.completed_actions.append("expedited_replacement_created")
            state.pending_confirmation = None
        else:
            response_prompt = [
                {
                    "role": "system",
                    "content": (
                        "You are the Bookly ResolutionAgent. The customer is considering a free expedited replacement for a delayed order. "
                        "Answer their concern briefly if they asked one, and then ask them to confirm before arranging the shipment."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Customer message: \"{message}\"\n"
                        "Provide a customer-facing response that answers the question and asks the customer to confirm whether they would like to go ahead with the expedited replacement."
                    ),
                },
            ]
            response = client.chat(response_prompt, temperature=0.5)
            state.pending_confirmation = {
                "action": "upgrade_shipping",
                "service_level": "expedited_replacement",
                "reason": "Customer is considering expedited replacement and needs explicit confirmation.",
            }
    else:
        response_prompt = [
            {
                "role": "system",
                "content": (
                    "You are the Bookly ResolutionAgent. The customer needs help choosing between refund and expedited replacement. "
                    "Ask for their preference in a clear, supportive way."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Customer message: \"{message}\"\n"
                    "Ask whether they would like to confirm the refund or accept an expedited replacement."
                ),
            },
        ]
        response = client.chat(response_prompt, temperature=0.5)

    traces.append(
        new_trace(
            type="customer_response_generated",
            agent="ResolutionAgent",
            title="Resolution response drafted",
            summary="Generated a customer-facing response for the resolution path.",
            outputs={"message": response},
        )
    )

    state.active_agent = "resolution"
    state.current_intent = "request_refund" if "refund" in action else "accept_expedited_shipping"
    return response, [trace.dict() for trace in traces]

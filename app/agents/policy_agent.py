from app.services.openai_client import OpenAIClient
from app.services.trace import new_trace
from app.tools.policy_tools import find_best_policy
from app.models import ConversationState


def handle_policy_intent(message: str, state: ConversationState) -> tuple[str, list[dict]]:
    traces = []
    policy = find_best_policy(message)
    client = OpenAIClient()

    traces.append(
        new_trace(
            type="policy_loaded",
            agent="PolicyAgent",
            title="Policy lookup performed",
            summary="Searched Bookly policy documents for the customer’s question.",
            inputs={"message": message},
            outputs={"policy_found": bool(policy), "policy_name": policy.get("title") if policy else None},
        )
    )

    if policy:
        response_prompt = [
            {
                "role": "system",
                "content": (
                    "You are the Bookly PolicyAgent. Provide a customer-facing explanation based on the matched policy details. "
                    "Keep the tone professional and helpful."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Customer message: \"{message}\"\n"
                    f"Policy title: {policy.get('title')}\n"
                    f"Policy summary: {policy.get('summary')}\n"
                    f"Policy details: {policy.get('details')}\n"
                    "Answer the customer's question using this policy information."
                ),
            },
        ]
        response = client.chat(response_prompt, temperature=0.5)
    else:
        response_prompt = [
            {
                "role": "system",
                "content": (
                    "You are the Bookly PolicyAgent. The customer has asked a question that does not match local policy. "
                    "Explain honestly that the policy is not available and offer to escalate to a human specialist."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Customer message: \"{message}\"\n"
                    "Provide a response that sets correct expectations and asks if the customer wants human escalation."
                ),
            },
        ]
        response = client.chat(response_prompt, temperature=0.5)

    traces.append(
        new_trace(
            type="customer_response_generated",
            agent="PolicyAgent",
            title="Policy response drafted",
            summary="Generated a customer-facing policy response.",
            outputs={"message": response},
        )
    )

    state.active_agent = "policy"
    state.current_intent = "ask_policy"
    return response, [trace.dict() for trace in traces]

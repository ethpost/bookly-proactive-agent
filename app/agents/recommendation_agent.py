from app.services.openai_client import OpenAIClient
from app.services.trace import new_trace
from app.tools.order_tools import get_order
from app.tools.recommendation_tools import recommend_similar_items
from app.models import ConversationState


def handle_recommendation_intent(message: str, state: ConversationState, decision: dict) -> tuple[str, list[dict]]:
    traces = []
    order = get_order(state.order_id)
    recommendation_data = recommend_similar_items(state.order_id, state.known_need_by)

    traces.append(
        new_trace(
            type="tool_call",
            agent="RecommendationAgent",
            title="recommend_similar_items",
            summary="Retrieved alternative items that can arrive before the customer’s need-by date.",
            inputs={"order_id": state.order_id, "need_by": state.known_need_by},
            outputs=recommendation_data,
        )
    )

    client = OpenAIClient()
    recommendations = recommendation_data["recommendations"]
    item_titles = [item["title"] for item in recommendations]

    prompt = [
        {
            "role": "system",
            "content": (
                "You are the Bookly RecommendationAgent. The customer is looking for a similar item or an alternative gift that can arrive on time. "
                "Use the original order details and recommended items to create a concise, empathetic response. "
                "Frame these as recovery options that could be chosen instead of a full refund. "
                "Do not mention internal systems or tool calls."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Customer message: \"{message}\"\n"
                f"Original item: {order.get('item')}\n"
                f"Need-by date: {state.known_need_by}\n"
                f"Alternative recommendations: {recommendations}\n"
                "If the customer asked for an alternative to a refund, say this can be a great option to keep the celebration on track. "
                "If the customer has follow-up questions about any listed item, answer using the item attributes included here."
            ),
        },
    ]

    response = client.chat(prompt, temperature=0.6)
    state.active_agent = "recommendation"
    state.current_intent = "recommend_similar_items"
    state.offered_options = item_titles
    state.last_recommendations = recommendations
    state.pending_recommendation = False

    traces.append(
        new_trace(
            type="customer_response_generated",
            agent="RecommendationAgent",
            title="Recommendation response drafted",
            summary="Generated a customer-facing recommendation message for alternate on-time items.",
            outputs={"message": response},
        )
    )

    return response, [trace.dict() for trace in traces]

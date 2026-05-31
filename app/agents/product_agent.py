from app.services.openai_client import OpenAIClient
from app.services.trace import new_trace
from app.tools.order_tools import get_order
from app.tools.product_tools import find_best_product_match
from app.models import ConversationState


def handle_product_intent(message: str, state: ConversationState, decision: dict) -> tuple[str, list[dict]]:
    traces = []
    recommendations = state.last_recommendations or []
    original_item = get_order(state.order_id).get("item")

    selected_item = find_best_product_match(message, recommendations) if recommendations else {}
    if not selected_item and recommendations:
        selected_item = recommendations[0]

    traces.append(
        new_trace(
            type="tool_call",
            agent="ProductAgent",
            title="select_recommended_product",
            summary="Selected the recommended product that best matches the customer’s follow-up question.",
            inputs={"message": message, "recommendations": [item.get("title") for item in recommendations]},
            outputs={"selected_product": selected_item},
        )
    )

    client = OpenAIClient()
    prompt = [
        {
            "role": "system",
            "content": (
                "You are the Bookly ProductAgent. A customer has already been offered some replacement products and now wants more detail on one of them. "
                "Use the selected product attributes to answer clearly and helpfully. "
                "Do not mention internals or tool calls."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Customer message: \"{message}\"\n"
                f"Original item: {original_item}\n"
                f"Selected product: {selected_item.get('title')}\n"
                f"Description: {selected_item.get('description')}\n"
                f"Price: ${selected_item.get('price')}\n"
                f"Estimated delivery: {selected_item.get('estimated_delivery')}\n"
                f"Shipping speed: {selected_item.get('shipping_speed')}\n"
                f"Dimensions: {selected_item.get('dimensions')}\n"
                f"Color: {selected_item.get('color')}\n"
                f"Brand: {selected_item.get('brand')}\n"
                "Answer the customer’s question with product-specific details and explain why this is a good on-time alternative."
            ),
        },
    ]

    response = client.chat(prompt, temperature=0.6)
    state.active_agent = "product"
    state.current_intent = "ask_product_details"

    traces.append(
        new_trace(
            type="customer_response_generated",
            agent="ProductAgent",
            title="Product detail response drafted",
            summary="Generated a customer-facing product detail response based on the selected recommendation.",
            outputs={"message": response},
        )
    )

    return response, [trace.dict() for trace in traces]

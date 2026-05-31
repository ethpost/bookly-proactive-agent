from app.tools.order_tools import get_order
from app.tools.product_tools import search_alternatives


def recommend_similar_items(order_id: str, need_by: str) -> dict:
    order = get_order(order_id)
    item = order.get("item", "")
    recommended = search_alternatives(item, need_by)
    return {
        "order_id": order_id,
        "need_by": need_by,
        "original_item": item,
        "recommendations": recommended["recommendations"],
    }

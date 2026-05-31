def get_tracking_status(order_id: str) -> dict:
    return {
        "order_id": order_id,
        "status": "Delayed by carrier",
        "original_eta": "Friday",
        "current_eta": "Tuesday",
        "delay_reason": "Carrier delay during transit",
        "notes": "Updated ETA misses the customer’s stated need-by date.",
    }


def estimate_delivery_options(order_id: str, need_by: str) -> dict:
    options = [
        {
            "name": "standard_delivery",
            "description": "Current order is expected Tuesday, no change.",
            "arrival": "Tuesday",
            "meets_need_by": False,
        },
        {
            "name": "expedited_replacement",
            "description": "Free expedited replacement arrives Saturday by 10 PM.",
            "arrival": "Saturday by 10 PM",
            "meets_need_by": False,
        },
        {
            "name": "local_pickup",
            "description": "Local pickup is unavailable for this order.",
            "arrival": None,
            "meets_need_by": False,
        },
    ]
    return {
        "order_id": order_id,
        "need_by": need_by,
        "options": options,
        "summary": "Expedited replacement is the fastest available option for this order.",
    }

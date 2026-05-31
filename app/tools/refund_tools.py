def check_refund_eligibility(order_id: str, reason: str, need_by: str) -> dict:
    eligible = True
    return {
        "order_id": order_id,
        "eligible": eligible,
        "reason": "Delivery delay misses stated need-by date.",
        "refund_amount": 34.98,
        "explanation": (
            "A refund is eligible because the delivery delay causes the order to miss the customer’s need-by date."
        ),
    }


def issue_refund(order_id: str, amount: float, reason: str) -> dict:
    return {
        "order_id": order_id,
        "status": "refunded",
        "amount": amount,
        "reason": reason,
        "confirmation_code": "REFUND-1001",
    }


def upgrade_shipping(order_id: str, service_level: str) -> dict:
    return {
        "order_id": order_id,
        "status": "shipping_upgraded",
        "service_level": service_level,
        "arrival": "Saturday by 10 PM",
        "cost": "free",
        "description": "Free expedited replacement is ready to ship.",
    }

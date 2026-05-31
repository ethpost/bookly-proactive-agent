import json
from pathlib import Path
from copy import deepcopy

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load_json(name: str) -> dict:
    path = _DATA_DIR / name
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)

ORDERS = _load_json("orders.json")
CUSTOMER_MEMORY = _load_json("customer_memory.json")


def get_order(order_id: str) -> dict:
    order = ORDERS.get(order_id)
    return deepcopy(order) if order else {}


def get_customer_memory(customer_id: str) -> dict:
    memory = CUSTOMER_MEMORY.get(customer_id)
    return deepcopy(memory) if memory else {}

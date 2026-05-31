import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load_json(name: str) -> dict:
    path = _DATA_DIR / name
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)

PRODUCTS = _load_json("products.json")


def get_product(product_id: str) -> dict:
    return deepcopy(PRODUCTS.get(product_id, {}))


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


def _weekday_rank(day_string: str) -> int:
    mapping = {
        "monday": 1,
        "tuesday": 2,
        "wednesday": 3,
        "thursday": 4,
        "friday": 5,
        "saturday": 6,
        "sunday": 7,
    }
    tokens = _tokenize(day_string)
    for token in tokens:
        if token in mapping:
            return mapping[token]
    return 7


def search_alternatives(original_item: str, need_by: str, max_results: int = 3) -> dict:
    original_tokens = set(_tokenize(original_item))
    need_by_rank = _weekday_rank(need_by)
    scored: List[tuple[int, dict]] = []

    for product in PRODUCTS.values():
        if not product.get("available", False):
            continue

        delivery_rank = _weekday_rank(product.get("estimated_delivery", "Sunday"))
        availability_score = 1 if delivery_rank <= need_by_rank else 0

        text = " ".join(
            [product.get("title", ""), product.get("description", ""), " ".join(product.get("tags", []))]
        )
        product_tokens = set(_tokenize(text))
        relevance_score = sum(1 for token in original_tokens if token in product_tokens)

        score = relevance_score * 10 + availability_score
        if score > 0:
            scored.append((score, product))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    recommendations = [deepcopy(product) for _, product in scored[:max_results]]

    if not recommendations:
        recommendations = [deepcopy(product) for product in PRODUCTS.values() if product.get("available", False)][:max_results]

    return {
        "original_item": original_item,
        "need_by": need_by,
        "recommendations": recommendations,
    }


def find_best_product_match(query: str, products: List[dict]) -> dict:
    query_tokens = set(_tokenize(query))
    best_match = None
    best_score = 0

    for product in products:
        text = " ".join([product.get("title", ""), product.get("description", ""), " ".join(product.get("tags", []))])
        product_tokens = set(_tokenize(text))
        score = sum(1 for token in query_tokens if token in product_tokens)
        if score > best_score:
            best_score = score
            best_match = product

    return best_match or (products[0] if products else {})

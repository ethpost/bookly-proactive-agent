import json
import re
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load_json(name: str) -> dict:
    path = _DATA_DIR / name
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)

POLICIES = _load_json("policies.json")


def get_policy(policy_name: str) -> dict:
    return POLICIES.get(policy_name, {})


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def search_policies(query: str) -> list[dict]:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    scored: list[tuple[int, dict]] = []
    for policy in POLICIES.values():
        text = " ".join(str(value).lower() for value in policy.values())
        policy_tokens = set(_tokenize(text))
        score = sum(1 for token in query_tokens if token in policy_tokens)
        if score > 0:
            scored.append((score, policy))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [policy for _, policy in scored]


def find_best_policy(query: str) -> Any:
    matches = search_policies(query)
    return matches[0] if matches else None

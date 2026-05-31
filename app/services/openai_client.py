"""Lightweight OpenAI HTTP client using requests to avoid SDK auth issues."""
from typing import Any, Dict, List
import os
import requests
from app.config import OPENAI_API_KEY, OPENAI_MODEL

API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIClient:
    def __init__(self, model: str = OPENAI_API_MODEL if False else OPENAI_MODEL):
        key = OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is required. Set it in .env or env vars.")
        self.api_key = key
        self.model = model

    def chat(self, messages: List[Dict[str, Any]], temperature: float = 0.2) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 512,
        }
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            # surface provider message for easier debugging
            raise RuntimeError(f"OpenAI API error: {resp.status_code} {resp.text}") from exc
        data = resp.json()
        # Defensive navigation of response
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        return message.get("content", "").strip()


def parse_json_response(raw: str) -> dict:
    import json, re

    text = raw.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    # last resort
    raise ValueError("Could not parse JSON from model output")

import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_supervisor_is_entrypoint_and_recommendation_routing():
    # Start scenario to get initial state
    r = client.post("/api/start")
    assert r.status_code == 200
    payload = r.json()
    state = payload["state"]

    # Send a customer message that should be routed to shipping first
    r2 = client.post("/api/message", json={"message": "ok, what are my options?", "state": state})
    assert r2.status_code == 200
    resp = r2.json()
    traces = resp.get("traces", [])
    # First trace should be supervisor classification
    assert traces[0]["agent"] == "SupervisorAgent"
    assert traces[0]["type"] == "intent_classification"
    assert traces[0]["outputs"].get("next_agent") == "shipping"

    # Shipping reply should include a soft offer for recommendations and set pending_recommendation
    message = resp.get("message", "")
    assert "recommend" in message.lower() or "alternative" in message.lower()
    state = resp.get("state")
    assert state.get("pending_recommendation") is True

    # Now customer accepts the recommendation offer
    r3 = client.post("/api/message", json={"message": "yes please, show alternatives", "state": state})
    assert r3.status_code == 200
    resp2 = r3.json()
    traces2 = resp2.get("traces", [])
    # Ensure supervisor classified intent and routed to recommendation
    assert traces2[0]["agent"] == "SupervisorAgent"
    assert traces2[0]["type"] == "intent_classification"
    assert traces2[0]["outputs"].get("next_agent") == "recommendation"

    # Recommendation agent should generate a customer-facing message with options
    assert "recommend" in resp2.get("message", "").lower() or "arrival" in resp2.get("message", "").lower()


def test_policy_lookup_matches_upcharge_question():
    from app.tools.policy_tools import find_best_policy

    policy = find_best_policy(
        "If I choose a replacement item, will I have to pay the difference?"
    )
    assert policy is not None
    assert "upcharge" in policy.get("title", "").lower() or "replacement" in policy.get("summary", "").lower()


def test_product_tool_can_lookup_replacement_item_details():
    from app.tools.product_tools import get_product, search_alternatives

    recommendations = search_alternatives("birthday book", "Saturday morning")
    assert recommendations["recommendations"]
    product = get_product(recommendations["recommendations"][0]["id"])
    assert product
    assert "title" in product and "description" in product

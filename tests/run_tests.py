import sys
from pathlib import Path
# Ensure project root is on sys.path so `app` package is importable
ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Inject a dummy OpenAIClient to avoid external API calls during tests
import importlib
openai_mod = importlib.import_module("app.services.openai_client")


class DummyOpenAIClient:
    def __init__(self, model: str = None):
        self.model = model

    def chat(self, messages, temperature: float = 0.2):
        # Return a generic customer-facing response depending on the agent hint
        text = ""
        # Look for simple hints in the system prompt or user content
        joined = " ".join([m.get("content", "") for m in messages])
        if "ShippingAgent" in joined:
            return "We\'re sorry — the current shipment cannot arrive by Saturday. The fastest available recovery is a free expedited replacement arriving Saturday by 10 PM."
        if "RecommendationAgent" in joined:
            return "I can recommend several similar items that can arrive by Saturday: Personalized storybook bundle (arrives Friday), Interactive kids' storybook (arrives Friday)."
        if "ProductAgent" in joined:
            return "This item is a personalized storybook bundle with a customizable cover, estimated Friday delivery, and fast overnight shipping. It is lightweight and gift-ready."
        if "ResolutionAgent" in joined:
            return "I can confirm a refund or arrange an expedited replacement. Please confirm which you prefer."
        return "Thanks — we can help with that."

openai_mod.OpenAIClient = DummyOpenAIClient

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def run():
    try:
        # Start scenario
        r = client.post("/api/start")
        if r.status_code != 200:
            print("/api/start failed", r.status_code, r.text)
            return 2
        payload = r.json()
        state = payload["state"]

        r2 = client.post("/api/message", json={"message": "ok, what are my options?", "state": state})
        if r2.status_code != 200:
            print("/api/message (options) failed", r2.status_code, r2.text)
            return 3
        resp = r2.json()
        print("/api/message (options) response:", resp)
        traces = resp.get("traces", [])
        assert traces[0]["agent"] == "SupervisorAgent"
        assert traces[0]["type"] == "intent_classification"
        assert traces[0]["outputs"].get("next_agent") == "shipping"

        message = resp.get("message", "")
        print("Shipping message:", message)
        assert "recommend" in message.lower() or "alternative" in message.lower(), "Shipping message did not offer recommendation"
        state = resp.get("state")
        print("State after shipping:", state)
        assert state.get("pending_recommendation") is True

        r_confidence = client.post("/api/message", json={"message": "How confident are we that the expedited shipping will arrive by Saturday night?", "state": state})
        if r_confidence.status_code != 200:
            print("/api/message (confidence) failed", r_confidence.status_code, r_confidence.text)
            return 4
        resp_confidence = r_confidence.json()
        print("/api/message (confidence) response:", resp_confidence)
        assert resp_confidence["traces"][0]["agent"] == "SupervisorAgent"
        assert resp_confidence["traces"][0]["outputs"].get("next_agent") == "shipping"
        assert "confident" in resp_confidence.get("message", "").lower() or "arrive" in resp_confidence.get("message", "").lower()

        r3 = client.post("/api/message", json={"message": "yes please, show alternatives", "state": state})
        if r3.status_code != 200:
            print("/api/message (accept) failed", r3.status_code, r3.text)
            return 4
        resp2 = r3.json()
        print("/api/message (accept) response:", resp2)
        traces2 = resp2.get("traces", [])
        assert traces2[0]["agent"] == "SupervisorAgent"
        assert traces2[0]["type"] == "intent_classification"
        assert traces2[0]["outputs"].get("next_agent") == "recommendation"

        assert "recommend" in resp2.get("message", "").lower() or "arrival" in resp2.get("message", "").lower(), "Recommendation message did not include expected text"

        # Product detail follow-up after recommendation
        r_product = client.post("/api/message", json={"message": "Can you tell me more about the first option?", "state": resp2["state"]})
        if r_product.status_code != 200:
            print("/api/message (product detail) failed", r_product.status_code, r_product.text)
            return 5
        resp_product = r_product.json()
        print("/api/message (product detail) response:", resp_product)
        assert resp_product["traces"][0]["outputs"].get("next_agent") == "product", "Product detail follow-up should route to ProductAgent"
        assert "personalized" in resp_product.get("message", "").lower() or "storybook" in resp_product.get("message", "").lower(), "Product detail response should mention the recommended product"

        # Refund confirmation regression
        r4 = client.post("/api/start")
        if r4.status_code != 200:
            print("/api/start (refund) failed", r4.status_code, r4.text)
            return 6
        state2 = r4.json()["state"]

        r5 = client.post("/api/message", json={"message": "actually, just issue me a refund and I will go find something else", "state": state2})
        if r5.status_code != 200:
            print("/api/message (refund request) failed", r5.status_code, r5.text)
            return 7
        resp5 = r5.json()
        assert resp5["traces"][0]["outputs"].get("next_agent") == "resolution", "Refund request should route to ResolutionAgent"
        state2 = resp5["state"]
        assert state2.get("pending_confirmation"), "Refund request should create a pending confirmation"

        r6 = client.post("/api/message", json={"message": "proceed with refund", "state": state2})
        if r6.status_code != 200:
            print("/api/message (refund confirm) failed", r6.status_code, r6.text)
            return 8
        resp6 = r6.json()
        assert resp6["state"].get("refund_issued") is True, "Refund should be issued after confirmation"
        assert resp6["state"].get("pending_confirmation") is None, "Pending confirmation should clear after issuing refund"

        print("ALL TESTS PASSED")
        return 0
    except AssertionError as e:
        print("Assertion failed:", e)
        return 1
    except Exception as e:
        print("Error during tests:", e)
        return 5


if __name__ == '__main__':
    sys.exit(run())

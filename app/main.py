from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.services.state import create_initial_state, add_message
from app.agents.proactive_agent import create_proactive_message
from app.agents.supervisor import classify_customer_message
from app.agents.shipping_agent import handle_shipping_intent
from app.agents.resolution_agent import handle_resolution_intent
from app.agents.policy_agent import handle_policy_intent
from app.agents.product_agent import handle_product_intent
from app.agents.escalation_agent import handle_escalation_intent
from app.agents.recommendation_agent import handle_recommendation_intent
from app.services.trace import new_trace
from app.models import ConversationState

BASE_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Bookly Proactive Agent")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

INDEX_HTML = STATIC_DIR / "index.html"


def _build_state_payload(state: ConversationState) -> dict:
    payload = state.dict()
    return payload


def _join_traces(*trace_groups: list[dict]) -> list[dict]:
    traces = []
    for group in trace_groups:
        if isinstance(group, list):
            traces.extend(group)
        elif isinstance(group, dict):
            traces.append(group)
    return traces


@app.get("/", response_class=HTMLResponse)
async def root():
    if not INDEX_HTML.exists():
        raise HTTPException(status_code=404, detail="Index page not found")
    return HTMLResponse(INDEX_HTML.read_text(encoding="utf-8"))


@app.post("/api/start")
async def api_start():
    state = create_initial_state()
    message, traces = create_proactive_message(state)
    add_message(state, "agent", message)
    return {
        "message": message,
        "state": _build_state_payload(state),
        "traces": traces,
    }


@app.post("/api/message")
async def api_message(payload: dict):
    message = payload.get("message")
    state_data = payload.get("state")
    if message is None or state_data is None:
        raise HTTPException(status_code=400, detail="message and state are required")

    state = ConversationState.parse_obj(state_data)
    add_message(state, "customer", message)

    decision, supervisor_trace = classify_customer_message(message, state)
    traces = [supervisor_trace]

    if decision.get("requires_clarification"):
        response = decision.get(
            "clarifying_question",
            "Could you clarify what you’d like help with regarding your order?",
        )
        traces.append(
            new_trace(
                type="clarification_requested",
                agent="SupervisorAgent",
                title="Clarification requested",
                summary="The supervisor requested a clearer customer intent before proceeding.",
                outputs={"question": response},
            ).dict()
        )
    else:
        next_agent = decision.get("next_agent")
        if next_agent == "shipping":
            response, agent_traces = handle_shipping_intent(message, state)
            traces.extend(agent_traces)
        elif next_agent == "resolution":
            response, agent_traces = handle_resolution_intent(message, state, decision)
            traces.extend(agent_traces)
        elif next_agent == "recommendation":
            response, agent_traces = handle_recommendation_intent(message, state, decision)
            traces.extend(agent_traces)
        elif next_agent == "product":
            response, agent_traces = handle_product_intent(message, state, decision)
            traces.extend(agent_traces)
        elif next_agent == "policy":
            response, agent_traces = handle_policy_intent(message, state)
            traces.extend(agent_traces)
        elif next_agent == "escalation":
            response, agent_traces = handle_escalation_intent(state)
            traces.extend(agent_traces)
        else:
            response = (
                "I’m here to help. Could you tell me whether you want a refund, "
                "an expedited replacement, or to talk to a human?"
            )
            traces.append(
                new_trace(
                    type="guardrail",
                    agent="SupervisorAgent",
                    title="Fallback routing",
                    summary="Supervisor did not determine a clear action, so the agent asked for a clearer request.",
                ).dict()
            )

    add_message(state, "agent", response)
    return {
        "message": response,
        "state": _build_state_payload(state),
        "traces": traces,
    }


@app.post("/api/reset")
async def api_reset():
    state = create_initial_state()
    response = "Scenario reset. Bookly is monitoring the delayed order and will reach out proactively."
    trace = new_trace(
        type="operational_event",
        agent="API",
        title="Scenario reset",
        summary="Reset the delayed birthday gift scenario state.",
    )
    return {
        "message": response,
        "state": _build_state_payload(state),
        "traces": [trace.dict()],
    }

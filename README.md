# Bookly Proactive Agent

A Python-first AI agent prototype for a proactive customer support workflow at a fictional bookstore called Bookly.

## Project Overview

This demo shows a focused customer support scenario where Bookly detects a shipping delay for a time-sensitive order, reaches out proactively via an SMS-style interface, and manages a dynamic customer conversation.

## Why This Demo Exists

A great customer experience should not wait for the customer to report a problem. This prototype demonstrates a proactive support agent that:
- detects a shipment delay,
- engages the customer before a support ticket forms,
- routes the conversation with a supervisor model,
- uses deterministic tools for source-of-truth data,
- and keeps a detailed trace of decisions and actions.

## Architecture Overview

- `app/main.py` - FastAPI backend serving the UI and REST API.
- `app/services` - state, trace, and OpenAI client helpers.
- `app/agents` - orchestrated agents for proactive outreach, supervision, shipping, resolution, policy, and escalation.
- `app/tools` - deterministic mock tools for orders, shipping, refunds, policy, and escalation.
- `app/data` - fixed scenario data for the delayed birthday gift recovery case.
- `static/` - vanilla HTML/CSS/JS frontend with split-screen UI.

The LLM is used for message drafting and supervisor classification. Deterministic Python tools provide factual order status, policy checks, and action execution.

## Local Setup

1. Clone the repo.
2. Create a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and set your OpenAI API key.

## Environment Variables

Create a `.env` file with:

```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

## Run Locally

```bash
uvicorn app.main:app --reload
```

Then open `http://localhost:8000`.

## Supported Demo Paths

Try natural inputs like:
- "Why is it delayed?"
- "This is for a birthday party Saturday morning. Can you still get it here?"
- "What are my options?"
- "Saturday night is too late."
- "Just refund me."
- "Yes, refund it."
- "Actually can you just send the replacement?"
- "I want to talk to a person."
- "Why am I eligible for a refund?"
- "Can I get both the refund and the book?"
- "Never mind."

## Notes

- The OpenAI API key is never exposed to the frontend.
- The UI is a demo-only experience with mocked tools and no real payment or shipping integration.
- The trace panel surfaces operational events, agent handoffs, tool calls, guardrails, and completed actions.

## Deployment

Render deployment example:
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment variables:
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL`

## Known Limitations

- This is a fixed scenario prototype, not a production platform.
- It uses local JSON fixtures instead of a database.
- No real SMS provider or payment service is implemented.
- The flow is intentionally simple so it is easy to inspect and extend.

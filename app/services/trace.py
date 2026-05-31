import uuid
from datetime import datetime, timezone
from app.models import TraceEvent


def new_trace(
    type: str,
    agent: str,
    title: str,
    summary: str,
    inputs: dict | None = None,
    outputs: dict | None = None,
    metadata: dict | None = None,
) -> TraceEvent:
    return TraceEvent(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        type=type,
        agent=agent,
        title=title,
        summary=summary,
        inputs=inputs,
        outputs=outputs,
        metadata=metadata,
    )

"""
src/backend/routes_stream.py

Server-Sent Events endpoint streaming HIGH/CRITICAL alerts in real time to
the dashboard, backing View A's strobe/banner notification and View B's
live alert timeline. Consumes src.escalation_agent.event_bus.event_bus,
the same singleton the EscalationAgent publishes onto.
"""
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from src.escalation_agent.event_bus import event_bus

router = APIRouter(prefix="/api/stream", tags=["stream"])


@router.get("/alerts")
async def stream_alerts(request: Request):
    async def event_generator():
        async for event in event_bus.subscribe():
            if await request.is_disconnected():
                break
            if event is None:
                yield {"event": "heartbeat", "data": "ping"}
                continue
            yield {"event": "alert", "data": event.to_json()}

    return EventSourceResponse(event_generator())

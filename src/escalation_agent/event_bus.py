"""
src/escalation_agent/event_bus.py

Minimal in-process pub/sub: a single asyncio.Queue-backed broadcaster.
Chosen over a message broker (Kafka, managed pub/sub) per Green AI
analysis (docs/GREEN_AI.md) — there is exactly one consumer process (the
FastAPI backend) and event volumes are small, so no second always-on
service is justified.

Because the ABM pipeline (src/abm) runs synchronously and may be invoked
from a sync context (CLI batch run) or an async context (FastAPI request
handler), this bus exposes both a sync `publish()` and an async
`subscribe()` generator, bridged via a thread-safe queue.
"""
import asyncio
import json
import queue
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass
class AlertEvent:
    event_id: str
    timestamp: str
    clip_id: str
    zone: str
    behavior_class: str
    behavior_label: str
    severity: str
    description: str
    policy_section_ref: str

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class EventBus:
    def __init__(self):
        self._subscribers: list[queue.Queue] = []
        self._lock = threading.Lock()

    def publish(self, event: AlertEvent):
        with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            q.put_nowait(event)

    def _subscribe_sync(self) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        with self._lock:
            self._subscribers.append(q)
        return q

    def _unsubscribe_sync(self, q: queue.Queue):
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    async def subscribe(self):
        """Async generator yielding AlertEvent as they're published. Used
        directly by the FastAPI SSE route."""
        q = self._subscribe_sync()
        try:
            while True:
                try:
                    event = await asyncio.get_event_loop().run_in_executor(
                        None, q.get, True, 1.0
                    )
                    yield event
                except queue.Empty:
                    yield None  # heartbeat tick, route layer turns this into an SSE comment
        finally:
            self._unsubscribe_sync(q)


# Process-wide singleton — the ABM pipeline and the FastAPI app both import
# this same instance.
event_bus = EventBus()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

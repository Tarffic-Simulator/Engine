"""Use case for replaying persisted ticks and optionally following live events."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, Optional

from ..contracts.realtime_persistence import SimulationTickRepository
from ..contracts.realtime_streaming import TickStreamBroker


class ReplayAndStreamTicksUseCase:
    """Replay persisted history and then join the live stream when requested."""

    def __init__(
        self,
        tick_repository: SimulationTickRepository,
        stream_broker: Optional[TickStreamBroker] = None,
        tick_stream_broker: Optional[TickStreamBroker] = None,
    ) -> None:
        """Initialize the replay dependencies."""
        self.tick_repository = tick_repository
        self.stream_broker = stream_broker or tick_stream_broker

    async def execute(
        self,
        session_id: str,
        run_id: str,
        from_tick: int = -1,
        follow: bool = False,
        limit: int = 1000,
        last_event_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Return an async generator of SSE payload strings."""
        effective_from_tick = self._resolve_from_tick(from_tick=from_tick, last_event_id=last_event_id)

        async def _stream() -> AsyncIterator[str]:
            persisted_ticks = self.tick_repository.list_ticks_after(
                session_id=session_id,
                run_id=run_id,
                from_tick=effective_from_tick,
                limit=limit,
            )
            for tick_document in persisted_ticks:
                yield self._serialize_event(
                    event_name="tick",
                    event_id=str(tick_document["tick_number"]),
                    data=dict(tick_document),
                )

            if not follow or self.stream_broker is None:
                return

            async for live_event in self._stream_live_events(run_id):
                yield self._normalize_live_event(live_event)
                if self._event_name(live_event) == "run_status":
                    break

        return _stream()

    def _resolve_from_tick(self, from_tick: int, last_event_id: Optional[str]) -> int:
        """Apply Last-Event-ID precedence over from_tick when possible."""
        if last_event_id is not None:
            try:
                return int(last_event_id)
            except ValueError:
                return from_tick
        return from_tick

    async def _stream_live_events(self, run_id: str) -> AsyncIterator[Dict[str, Any]]:
        """Stream live events from the configured broker."""
        if hasattr(self.stream_broker, "subscribe"):
            async for event in self.stream_broker.subscribe(run_id):
                yield dict(event)
            return
        async for event in self.stream_broker.stream(run_id):
            yield dict(event)

    def _normalize_live_event(self, event: Dict[str, Any]) -> str:
        """Serialize a live broker event into SSE format."""
        event_name = self._event_name(event)
        event_id = str(event.get("id", event.get("tick_number", "")))
        payload = event.get("data", event)
        return self._serialize_event(event_name=event_name, event_id=event_id, data=payload)

    def _event_name(self, event: Dict[str, Any]) -> str:
        """Return the event type name for an event document."""
        return str(event.get("event", "tick"))

    def _serialize_event(self, event_name: str, event_id: str, data: Dict[str, Any]) -> str:
        """Serialize one event as a text/event-stream payload."""
        return f"event: {event_name}\nid: {event_id}\ndata: {json.dumps(data, default=str)}\n\n"
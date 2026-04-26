"""Use case for replaying persisted realtime ticks and following live public events."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, Iterable, Optional

from ..contracts.realtime_entities import is_terminal_public_status, normalize_public_status
from ..contracts.realtime_persistence import SimulationTickRepository
from ..contracts.realtime_streaming import TickStreamBroker


class StreamRealtimeEventsUseCase:
    """Provide a transport-neutral replay and live stream for realtime clients.

    Args:
        tick_repository: Repository used to replay persisted tick history.
        stream_broker: Live broker used to follow run events.
        tick_stream_broker: Backward-compatible alias for the live broker.
        clock: Optional UTC clock provider.
    """

    def __init__(
        self,
        tick_repository: SimulationTickRepository,
        stream_broker: Optional[TickStreamBroker] = None,
        tick_stream_broker: Optional[TickStreamBroker] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        """Initialize replay and live-stream dependencies.

        Args:
            tick_repository: Repository used to replay persisted tick history.
            stream_broker: Live broker used to follow run events.
            tick_stream_broker: Backward-compatible alias for the live broker.
            clock: Optional UTC clock provider.
        """
        self.tick_repository = tick_repository
        self.stream_broker = stream_broker or tick_stream_broker
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    async def execute(
        self,
        session_id: str,
        run_id: str,
        from_tick: int = -1,
        follow: bool = False,
        limit: int = 1000,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Return an async iterator of canonical realtime event envelopes.

        Args:
            session_id: Session identifier to stream.
            run_id: Run identifier to replay and follow.
            from_tick: Exclusive replay cursor.
            follow: Whether to continue with live broker events after replay.
            limit: Maximum number of persisted ticks to replay.

        Returns:
            Async iterator yielding public event envelopes.
        """

        async def _stream() -> AsyncIterator[Dict[str, Any]]:
            latest_cursor = from_tick
            persisted_ticks = self.tick_repository.list_ticks_after(
                session_id=session_id,
                run_id=run_id,
                from_tick=from_tick,
                limit=limit,
            )
            for tick_document in persisted_ticks:
                envelope = self._tick_envelope(
                    session_id=session_id,
                    run_id=run_id,
                    tick_document=tick_document,
                )
                latest_cursor = max(latest_cursor, int(envelope["cursor"]))
                yield envelope

            if not follow or self.stream_broker is None:
                return

            async for live_event in self._stream_live_events(run_id=run_id):
                envelope = self._normalize_live_event(
                    event=live_event,
                    session_id=session_id,
                    run_id=run_id,
                )
                if envelope["event"] == "tick" and int(envelope["cursor"]) <= latest_cursor:
                    continue
                latest_cursor = max(latest_cursor, int(envelope["cursor"]))
                yield envelope
                if envelope["event"] == "run_status" and envelope["data"].get("terminal"):
                    break

        return _stream()

    async def _stream_live_events(self, run_id: str) -> AsyncIterator[Dict[str, Any]]:
        """Yield live events from the configured broker.

        Args:
            run_id: Run identifier to subscribe to.

        Yields:
            Broker event dictionaries.
        """
        if hasattr(self.stream_broker, "subscribe"):
            async for event in self.stream_broker.subscribe(run_id):
                yield dict(event)
            return

        async for event in self.stream_broker.stream(run_id):
            yield dict(event)

    def _tick_envelope(
        self,
        session_id: str,
        run_id: str,
        tick_document: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build a public envelope for one persisted tick document.

        Args:
            session_id: Session identifier.
            run_id: Run identifier.
            tick_document: Persisted tick document.

        Returns:
            Public tick event envelope.
        """
        tick_number = int(tick_document.get("tick_number", -1))
        recorded_at = tick_document.get("recorded_at")
        return {
            "event": "tick",
            "session_id": session_id,
            "run_id": run_id,
            "cursor": tick_number,
            "sent_at": self._serialize_datetime(recorded_at) or self._serialize_datetime(self.clock()),
            "data": {
                "tick_number": tick_number,
                "recorded_at": self._serialize_datetime(recorded_at),
                "metrics": self._json_safe(tick_document.get("metrics") or {}),
                "snapshot": self._json_safe(tick_document.get("snapshot")),
                "events": self._json_safe(tick_document.get("events") or []),
            },
        }

    def _normalize_live_event(
        self,
        event: Dict[str, Any],
        session_id: str,
        run_id: str,
    ) -> Dict[str, Any]:
        """Normalize a broker event to the public realtime envelope contract.

        Args:
            event: Raw broker event.
            session_id: Fallback session identifier.
            run_id: Fallback run identifier.

        Returns:
            Public event envelope.
        """
        event_name = str(event.get("event", "tick"))
        payload = event.get("data", event)
        resolved_session_id = str(event.get("session_id") or payload.get("session_id") or session_id)
        resolved_run_id = str(event.get("run_id") or payload.get("run_id") or run_id)
        cursor = self._resolve_cursor(event=event, payload=payload)
        sent_at = self._serialize_datetime(event.get("sent_at")) or self._serialize_datetime(self.clock())

        if event_name == "run_status":
            public_status = normalize_public_status(payload.get("status"))
            terminal = payload.get("terminal")
            if terminal is None:
                terminal = is_terminal_public_status(public_status)
            normalized_payload = {
                "status": public_status,
                "terminal": bool(terminal),
                "error": self._json_safe(payload.get("error")),
            }
        elif event_name == "tick":
            normalized_payload = {
                "tick_number": int(payload.get("tick_number", cursor)),
                "recorded_at": self._serialize_datetime(payload.get("recorded_at")),
                "metrics": self._json_safe(payload.get("metrics") or {}),
                "snapshot": self._json_safe(payload.get("snapshot")),
                "events": self._json_safe(payload.get("events") or []),
            }
        else:
            normalized_payload = self._json_safe(payload)

        return {
            "event": event_name,
            "session_id": resolved_session_id,
            "run_id": resolved_run_id,
            "cursor": cursor,
            "sent_at": sent_at,
            "data": normalized_payload,
        }

    def _resolve_cursor(self, event: Dict[str, Any], payload: Dict[str, Any]) -> int:
        """Resolve a numeric replay cursor from a broker event.

        Args:
            event: Raw broker event.
            payload: Raw event payload.

        Returns:
            Numeric replay cursor.
        """
        for candidate in (
            event.get("cursor"),
            event.get("id"),
            event.get("tick_number"),
            payload.get("cursor"),
            payload.get("tick_number"),
        ):
            try:
                return int(candidate)
            except (TypeError, ValueError):
                continue
        return -1

    def _serialize_datetime(self, value: Any) -> Optional[str]:
        """Serialize a datetime-like value to an ISO-8601 string.

        Args:
            value: Candidate datetime value.

        Returns:
            ISO-8601 string when the value is datetime-like, otherwise ``None``.
        """
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, str):
            return value
        return None

    def _json_safe(self, value: Any) -> Any:
        """Recursively convert values to JSON-safe primitives.

        Args:
            value: Arbitrary nested value.

        Returns:
            JSON-safe nested structure.
        """
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(item) for item in value]
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
            return [self._json_safe(item) for item in value]
        if hasattr(value, "__dict__"):
            return self._json_safe(vars(value))
        return str(value)
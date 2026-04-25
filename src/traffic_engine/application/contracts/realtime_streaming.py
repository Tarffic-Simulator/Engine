"""Streaming contracts for realtime tick delivery."""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, Protocol


class TickStreamBroker(Protocol):
    """Abstraction for publishing and subscribing to run events."""

    def publish(self, run_id: str, event: Dict[str, Any]) -> None:
        """Publish one event synchronously for a run."""

    async def publish_tick(self, run_id: str, event: Dict[str, Any]) -> None:
        """Publish one event asynchronously for a run."""

    def subscribe(self, run_id: str) -> AsyncIterator[Dict[str, Any]]:
        """Subscribe to live events for a run."""

    def stream(self, run_id: str) -> AsyncIterator[Dict[str, Any]]:
        """Return a live event stream for a run."""
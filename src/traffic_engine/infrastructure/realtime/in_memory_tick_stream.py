"""In-memory live event broker for realtime tick streaming."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, AsyncIterator, DefaultDict, Dict, List


class InMemoryTickStreamBroker:
    """Simple in-process fan-out broker keyed by run identifier."""

    def __init__(self) -> None:
        """Initialize broker subscriber state."""
        self._subscribers: DefaultDict[str, List[asyncio.Queue]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def publish(self, run_id: str, event: Dict[str, Any]) -> None:
        """Publish one event without awaiting the caller."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self.publish_tick(run_id=run_id, event=event))

    async def publish_tick(self, run_id: str, event: Dict[str, Any]) -> None:
        """Publish one event to all current subscribers."""
        async with self._lock:
            subscribers = list(self._subscribers.get(run_id, []))
        for queue in subscribers:
            await queue.put(dict(event))

    async def publish_terminal_event(self, run_id: str, event: Dict[str, Any]) -> None:
        """Publish a terminal non-tick event for a run."""
        await self.publish_tick(run_id=run_id, event=event)

    async def subscribe(self, run_id: str) -> AsyncIterator[Dict[str, Any]]:
        """Yield live events for one run until a terminal event is received."""
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._subscribers[run_id].append(queue)
        try:
            while True:
                event = await queue.get()
                yield dict(event)
                if event.get("event") == "run_status":
                    break
        finally:
            async with self._lock:
                subscribers = self._subscribers.get(run_id, [])
                if queue in subscribers:
                    subscribers.remove(queue)
                if not subscribers and run_id in self._subscribers:
                    del self._subscribers[run_id]

    async def stream(self, run_id: str) -> AsyncIterator[Dict[str, Any]]:
        """Alias for subscribe to satisfy alternative stream protocol names."""
        async for event in self.subscribe(run_id):
            yield dict(event)
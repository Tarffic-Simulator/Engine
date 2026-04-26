"""Contract tests for canonical realtime WebSocket replay/follow behavior."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import inspect
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence

import pytest

from traffic_engine.api import realtime_router


def _resolve_method(target: Any, method_names: Sequence[str]) -> Any:
    for method_name in method_names:
        if hasattr(target, method_name):
            return getattr(target, method_name)
    pytest.fail(f"Expected one of methods {method_names} on {type(target).__name__}.")


def _instantiate_use_case(use_case_cls: type, dependencies: Dict[str, Any]) -> Any:
    init_signature = inspect.signature(use_case_cls.__init__)
    init_kwargs = {
        parameter_name: dependencies[parameter_name]
        for parameter_name in init_signature.parameters
        if parameter_name != "self" and parameter_name in dependencies
    }

    try:
        return use_case_cls(**init_kwargs)
    except TypeError as exc:
        pytest.fail(f"Could not instantiate {use_case_cls.__name__}: {exc}")


def _invoke_use_case(target: Any, method_names: Sequence[str], **call_args: Any) -> Any:
    method = _resolve_method(target, method_names)
    method_signature = inspect.signature(method)
    accepted_parameters = [
        parameter_name
        for parameter_name in method_signature.parameters
        if parameter_name != "self"
    ]
    accepted_kwargs = {
        parameter_name: call_args[parameter_name]
        for parameter_name in accepted_parameters
        if parameter_name in call_args
    }

    if not accepted_kwargs and len(accepted_parameters) == 1 and "request" in call_args:
        accepted_kwargs = {accepted_parameters[0]: call_args["request"]}

    result = method(**accepted_kwargs)
    return asyncio.run(result) if inspect.isawaitable(result) else result


async def _collect_async_items(async_iterator: AsyncIterator[Any], limit: int) -> List[Any]:
    items: List[Any] = []
    async for item in async_iterator:
        items.append(item)
        if len(items) >= limit:
            break
    return items


def _collect_stream_items(stream_result: Any, limit: int = 20) -> List[Any]:
    if hasattr(stream_result, "__aiter__"):
        return asyncio.run(_collect_async_items(stream_result, limit))

    if inspect.isawaitable(stream_result):
        awaited = asyncio.run(stream_result)
        return _collect_stream_items(awaited, limit=limit)

    if isinstance(stream_result, list):
        return stream_result[:limit]

    if isinstance(stream_result, tuple):
        return list(stream_result[:limit])

    if hasattr(stream_result, "__iter__") and not isinstance(stream_result, (str, bytes, dict)):
        return list(stream_result)[:limit]

    return [stream_result]


def _websocket_route() -> Any:
    for route in realtime_router.router.routes:
        if getattr(route, "path", "") == "/realtime/sessions/{session_id}/ws":
            return route
    pytest.fail("Missing websocket route '/realtime/sessions/{session_id}/ws' in realtime router.")


class _FakeTickRepository:
    def __init__(self, ticks: List[Dict[str, Any]]) -> None:
        self._ticks = list(ticks)

    def list_ticks_after(
        self,
        session_id: str,
        run_id: str,
        from_tick: int,
        limit: int,
    ) -> List[Dict[str, Any]]:
        matching = [
            tick
            for tick in self._ticks
            if tick["session_id"] == session_id
            and tick["run_id"] == run_id
            and tick["tick_number"] > from_tick
        ]
        matching.sort(key=lambda item: item["tick_number"])
        return [dict(item) for item in matching[:limit]]


class _FakeTickStreamBroker:
    def __init__(self, live_events: Optional[List[Dict[str, Any]]] = None) -> None:
        self._live_events = list(live_events or [])

    async def subscribe(self, run_id: str) -> AsyncIterator[Dict[str, Any]]:
        for event in self._live_events:
            yield dict(event)

    async def stream(self, run_id: str) -> AsyncIterator[Dict[str, Any]]:
        async for event in self.subscribe(run_id=run_id):
            yield dict(event)


class TestRealtimeWebSocketContracts:
    """Boundary tests for canonical WebSocket contracts introduced by ADR-016."""

    def test_websocket_route_exists_at_public_session_ws_path(self) -> None:
        # Arrange / Act
        route = _websocket_route()

        # Assert
        assert route.path == "/realtime/sessions/{session_id}/ws"

    def test_websocket_route_contract_exposes_replay_follow_inputs(self) -> None:
        # Arrange
        route = _websocket_route()

        # Act
        endpoint_parameters = set(inspect.signature(route.endpoint).parameters)

        # Assert
        assert {"session_id", "run_id", "from_tick", "follow"}.issubset(endpoint_parameters)

    def test_stream_realtime_events_replays_and_follows_with_public_event_envelopes(
        self,
        realtime_symbol_loader,
    ) -> None:
        # Arrange
        use_case_cls = realtime_symbol_loader(
            "traffic_engine.application.use_cases.stream_realtime_events",
            "StreamRealtimeEventsUseCase",
        )
        tick_repository = _FakeTickRepository(
            ticks=[
                {
                    "session_id": "session-realtime-001",
                    "run_id": "run-realtime-001",
                    "tick_number": 1,
                    "recorded_at": datetime.now(timezone.utc),
                    "metrics": {"density": 0.2},
                    "snapshot": {"tick": 1},
                    "events": [],
                }
            ]
        )
        stream_broker = _FakeTickStreamBroker(
            live_events=[
                {
                    "event": "run_status",
                    "session_id": "session-realtime-001",
                    "run_id": "run-realtime-001",
                    "cursor": 1,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "data": {
                        "status": "finished",
                        "terminal": True,
                        "error": None,
                    },
                }
            ]
        )
        use_case = _instantiate_use_case(
            use_case_cls,
            {
                "tick_repository": tick_repository,
                "stream_broker": stream_broker,
                "tick_stream_broker": stream_broker,
            },
        )

        # Act
        events = _collect_stream_items(
            _invoke_use_case(
                use_case,
                ("execute", "stream", "__call__"),
                session_id="session-realtime-001",
                run_id="run-realtime-001",
                from_tick=0,
                follow=True,
                limit=50,
            ),
            limit=5,
        )
        first_event = events[0]
        terminal_event = events[-1]

        # Assert
        assert (
            first_event.get("event"),
            first_event.get("session_id"),
            first_event.get("run_id"),
            isinstance(first_event.get("cursor"), int),
            isinstance(first_event.get("sent_at"), str),
            first_event.get("data", {}).get("tick_number"),
            terminal_event.get("event"),
            terminal_event.get("data", {}).get("status"),
            terminal_event.get("data", {}).get("terminal"),
        ) == (
            "tick",
            "session-realtime-001",
            "run-realtime-001",
            True,
            True,
            1,
            "run_status",
            "finished",
            True,
        )

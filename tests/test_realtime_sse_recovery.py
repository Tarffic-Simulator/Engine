"""Contract tests for realtime SSE replay and reconnect recovery behavior."""

from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any, AsyncIterator, Awaitable, Dict, List, Optional, Sequence

import pytest

async def _resolve_awaitable(awaitable: Awaitable[Any]) -> Any:
    return await awaitable


def _instantiate_use_case(use_case_cls: type, dependencies: Dict[str, Any]) -> Any:
    init_signature = inspect.signature(use_case_cls.__init__)
    init_kwargs = {
        name: dependencies[name]
        for name in init_signature.parameters
        if name != "self" and name in dependencies
    }

    try:
        return use_case_cls(**init_kwargs)
    except TypeError as exc:
        pytest.fail(f"Could not instantiate {use_case_cls.__name__}: {exc}")


def _resolve_method(target: Any, method_names: Sequence[str]) -> Any:
    for method_name in method_names:
        if hasattr(target, method_name):
            return getattr(target, method_name)
    pytest.fail(f"Expected one of methods {method_names} on {type(target).__name__}.")


def _invoke_use_case(
    target: Any,
    method_names: Sequence[str],
    **call_args: Any,
) -> Any:
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
    return asyncio.run(_resolve_awaitable(result)) if inspect.isawaitable(result) else result


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
        awaited = asyncio.run(_resolve_awaitable(stream_result))
        return _collect_stream_items(awaited, limit=limit)

    if isinstance(stream_result, list):
        return stream_result[:limit]

    if isinstance(stream_result, tuple):
        return list(stream_result[:limit])

    if hasattr(stream_result, "__iter__") and not isinstance(stream_result, (str, bytes, dict)):
        return list(stream_result)[:limit]

    return [stream_result]


def _parse_sse_payload(payload: str) -> Dict[str, Any]:
    event_type = ""
    event_id = ""
    data_text = ""

    for line in payload.splitlines():
        if line.startswith("event:"):
            event_type = line.split(":", 1)[1].strip()
        if line.startswith("id:"):
            event_id = line.split(":", 1)[1].strip()
        if line.startswith("data:"):
            data_text = line.split(":", 1)[1].strip()

    try:
        parsed_data = json.loads(data_text) if data_text else {}
    except json.JSONDecodeError:
        parsed_data = {"raw": data_text}

    return {
        "event": event_type,
        "id": event_id,
        "data": parsed_data,
    }


def _normalize_event(raw_event: Any) -> Dict[str, Any]:
    if isinstance(raw_event, str):
        return _parse_sse_payload(raw_event)

    if isinstance(raw_event, dict):
        event_name = str(raw_event.get("event", "tick"))
        event_id = str(raw_event.get("id", raw_event.get("tick_number", "")))
        data = raw_event.get("data", raw_event)
        parsed_data = data
        if isinstance(data, str):
            try:
                parsed_data = json.loads(data)
            except json.JSONDecodeError:
                parsed_data = {"raw": data}
        return {
            "event": event_name,
            "id": event_id,
            "data": parsed_data,
        }

    return {
        "event": "tick",
        "id": "",
        "data": raw_event,
    }


def _tick_event_ids(events: List[Dict[str, Any]]) -> List[str]:
    return [event["id"] for event in events if event.get("event") == "tick"]


def _first_tick_event(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    return next((event for event in events if event.get("event") == "tick"), {})


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


class TestSseReplayAndRecovery:
    """Behavior tests for replay and reconnect semantics over SSE."""

    def test_replays_persisted_ticks_after_from_tick_in_order(
        self,
        realtime_symbol_loader,
    ) -> None:
        # Arrange
        use_case_cls = realtime_symbol_loader(
            "traffic_engine.application.use_cases.replay_and_stream_ticks",
            "ReplayAndStreamTicksUseCase",
        )
        tick_repository = _FakeTickRepository(
            ticks=[
                {
                    "session_id": "session-realtime-001",
                    "run_id": "run-realtime-001",
                    "tick_number": 0,
                    "metrics": {"density": 0.1},
                },
                {
                    "session_id": "session-realtime-001",
                    "run_id": "run-realtime-001",
                    "tick_number": 1,
                    "metrics": {"density": 0.2},
                },
                {
                    "session_id": "session-realtime-001",
                    "run_id": "run-realtime-001",
                    "tick_number": 2,
                    "metrics": {"density": 0.3},
                },
            ]
        )
        stream_broker = _FakeTickStreamBroker(live_events=[])
        use_case = _instantiate_use_case(
            use_case_cls,
            {
                "tick_repository": tick_repository,
                "stream_broker": stream_broker,
                "tick_stream_broker": stream_broker,
            },
        )

        # Act
        raw_events = _collect_stream_items(
            _invoke_use_case(
                use_case,
                ("execute", "stream", "__call__"),
                session_id="session-realtime-001",
                run_id="run-realtime-001",
                from_tick=0,
                follow=False,
                limit=50,
            )
        )
        normalized_events = [_normalize_event(item) for item in raw_events]

        # Assert
        assert _tick_event_ids(normalized_events) == ["1", "2"]

    def test_honors_last_event_id_over_from_tick_for_reconnect(
        self,
        realtime_symbol_loader,
    ) -> None:
        # Arrange
        use_case_cls = realtime_symbol_loader(
            "traffic_engine.application.use_cases.replay_and_stream_ticks",
            "ReplayAndStreamTicksUseCase",
        )
        tick_repository = _FakeTickRepository(
            ticks=[
                {
                    "session_id": "session-realtime-001",
                    "run_id": "run-realtime-001",
                    "tick_number": 0,
                    "metrics": {"density": 0.1},
                },
                {
                    "session_id": "session-realtime-001",
                    "run_id": "run-realtime-001",
                    "tick_number": 1,
                    "metrics": {"density": 0.2},
                },
                {
                    "session_id": "session-realtime-001",
                    "run_id": "run-realtime-001",
                    "tick_number": 2,
                    "metrics": {"density": 0.3},
                },
            ]
        )
        stream_broker = _FakeTickStreamBroker(live_events=[])
        use_case = _instantiate_use_case(
            use_case_cls,
            {
                "tick_repository": tick_repository,
                "stream_broker": stream_broker,
                "tick_stream_broker": stream_broker,
            },
        )

        # Act
        raw_events = _collect_stream_items(
            _invoke_use_case(
                use_case,
                ("execute", "stream", "__call__"),
                session_id="session-realtime-001",
                run_id="run-realtime-001",
                from_tick=0,
                last_event_id="1",
                follow=False,
                limit=50,
            )
        )
        normalized_events = [_normalize_event(item) for item in raw_events]

        # Assert
        assert _tick_event_ids(normalized_events) == ["2"]

    def test_serializes_tick_event_with_id_equal_to_tick_number(
        self,
        realtime_symbol_loader,
    ) -> None:
        # Arrange
        use_case_cls = realtime_symbol_loader(
            "traffic_engine.application.use_cases.replay_and_stream_ticks",
            "ReplayAndStreamTicksUseCase",
        )
        tick_repository = _FakeTickRepository(
            ticks=[
                {
                    "session_id": "session-realtime-001",
                    "run_id": "run-realtime-001",
                    "tick_number": 2,
                    "metrics": {"density": 0.3},
                }
            ]
        )
        stream_broker = _FakeTickStreamBroker(live_events=[])
        use_case = _instantiate_use_case(
            use_case_cls,
            {
                "tick_repository": tick_repository,
                "stream_broker": stream_broker,
                "tick_stream_broker": stream_broker,
            },
        )

        # Act
        raw_events = _collect_stream_items(
            _invoke_use_case(
                use_case,
                ("execute", "stream", "__call__"),
                session_id="session-realtime-001",
                run_id="run-realtime-001",
                from_tick=1,
                follow=False,
                limit=50,
            )
        )
        normalized_events = [_normalize_event(item) for item in raw_events]
        first_tick_event = _first_tick_event(normalized_events)

        # Assert
        assert (
            first_tick_event.get("event"),
            first_tick_event.get("id"),
            first_tick_event.get("data", {}).get("tick_number"),
        ) == ("tick", "2", 2)

"""Contract tests for lane-aware realtime tick persistence and replay payloads."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional

from traffic_engine.application.use_cases.replay_and_stream_ticks import ReplayAndStreamTicksUseCase
from traffic_engine.application.use_cases.run_realtime_session import RunRealtimeSessionUseCase
from traffic_engine.infrastructure.runtime.manager_backed_simulation_model import (
    ManagerBackedSimulationModel,
)


class _FakeSessionRepository:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.sessions: Dict[str, Dict[str, Any]] = {
            "session-lane-001": {
                "session_id": "session-lane-001",
                "created_at": now,
                "updated_at": now,
                "status": "pending",
                "simulation_parameters": {"area": "Roma Norte", "config": {}, "max_ticks": 2},
            }
        }

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self.sessions.get(session_id)
        return dict(session) if session else None

    def update_session_status(self, session_id: str, status: str, updated_at: datetime) -> None:
        self.sessions[session_id]["status"] = status
        self.sessions[session_id]["updated_at"] = updated_at

    def update_session_latest_tick(
        self,
        session_id: str,
        run_id: str,
        tick_number: int,
        latest_metrics: Dict[str, Any],
        updated_at: datetime,
    ) -> None:
        self.sessions[session_id]["latest_run_id"] = run_id
        self.sessions[session_id]["latest_tick"] = tick_number
        self.sessions[session_id]["latest_metrics"] = dict(latest_metrics)
        self.sessions[session_id]["updated_at"] = updated_at


class _FakeRunRepository:
    def __init__(self) -> None:
        self.started: List[str] = []
        self.completed: List[str] = []

    def mark_run_started(self, run_id: str, started_at: datetime, worker_id: str) -> None:
        self.started.append(run_id)

    def mark_run_completed(self, run_id: str, completed_at: datetime) -> None:
        self.completed.append(run_id)

    def mark_run_failed(self, run_id: str, completed_at: datetime, error: Dict[str, Any]) -> None:
        raise RuntimeError(f"Unexpected run failure for '{run_id}': {error}")


class _FakeTickRepository:
    def __init__(self) -> None:
        self.persisted_ticks: List[Dict[str, Any]] = []

    def append_tick(self, tick: Dict[str, Any]) -> Dict[str, Any]:
        self.persisted_ticks.append(dict(tick))
        return dict(tick)

    def list_ticks_after(
        self,
        session_id: str,
        run_id: str,
        from_tick: int,
        limit: int,
    ) -> List[Dict[str, Any]]:
        matching = [
            tick
            for tick in self.persisted_ticks
            if tick.get("session_id") == session_id
            and tick.get("run_id") == run_id
            and int(tick.get("tick_number", -1)) > from_tick
        ]
        matching.sort(key=lambda item: int(item["tick_number"]))
        return matching[:limit]


class _FakeTickStreamBroker:
    def __init__(self) -> None:
        self.published: List[Dict[str, Any]] = []

    async def publish_tick(self, run_id: str, event: Dict[str, Any]) -> None:
        self.published.append({"run_id": run_id, "event": dict(event)})

    async def publish_terminal_event(self, run_id: str, event: Dict[str, Any]) -> None:
        self.published.append({"run_id": run_id, "event": dict(event)})

    async def subscribe(self, run_id: str) -> AsyncIterator[Dict[str, Any]]:
        if False:
            yield {"run_id": run_id}


class _FakeSimulationModel:
    def __init__(self) -> None:
        self._stepped = False

    def step(self) -> Any:
        if self._stepped:
            return {"tick": 2}, {"tick": 2, "density": 0.25}, True

        self._stepped = True
        return (
            {
                "tick": 1,
                "vehicles": [
                    {
                        "id": 70,
                        "type": "bus",
                        "lane_index": 1,
                        "lateral_offset_m": 1.75,
                        "render_label": "BUS",
                        "render_color": "#f39c12",
                    }
                ],
                "edges": {
                    "('A', 'B', 0)": {
                        "n_lanes": 2,
                        "occupancy_cells_lane_major": [[0, 70, 0], [0, 0, 0]],
                    }
                },
            },
            {"tick": 1, "density": 0.2},
            True,
        )


async def _collect_async_stream(stream: AsyncIterator[str], limit: int = 10) -> List[str]:
    """Collect at most `limit` payloads from an async stream."""
    payloads: List[str] = []
    async for payload in stream:
        payloads.append(payload)
        if len(payloads) >= limit:
            break
    return payloads


def _extract_sse_data(payload: str) -> Dict[str, Any]:
    """Extract the JSON dictionary from one SSE payload string."""
    data_line = next(
        line for line in payload.splitlines() if line.startswith("data:")
    )
    json_payload = data_line.split(":", 1)[1].strip()
    return json.loads(json_payload)


class _FakeCreateSimulationResponse:
    success = True
    simulation_id = "sim-manager-001"
    error = ""


class _FakeStepSimulationResponse:
    success = True
    new_tick = 1
    metrics = {"tick": 1, "density": 0.2}
    error = ""


class _FakeSimulationManager:
    def create_simulation(self, request: Any) -> Any:
        return _FakeCreateSimulationResponse()

    def step_simulation(self, simulation_id: str, request: Any) -> Any:
        return _FakeStepSimulationResponse()

    def get_snapshot(self, simulation_id: str, request: Any) -> Any:
        return {
            "success": True,
            "snapshot": {
                "vehicles": [{"id": 1, "lane_index": 1}],
                "edges": {"('A', 'B', 0)": {"n_lanes": 2}},
            },
        }


class TestRealtimeLanePayloadContracts:
    """Realtime behavior contracts for additive lane payload persistence and replay."""

    def test_run_realtime_session_when_snapshot_has_lane_fields_persists_them_in_tick_repository(
        self,
    ) -> None:
        """Persisted tick documents should preserve lane-aware vehicle and edge fields."""
        # Arrange
        session_repository = _FakeSessionRepository()
        run_repository = _FakeRunRepository()
        tick_repository = _FakeTickRepository()
        stream_broker = _FakeTickStreamBroker()
        use_case = RunRealtimeSessionUseCase(
            session_repository=session_repository,
            run_repository=run_repository,
            tick_repository=tick_repository,
            stream_broker=stream_broker,
            simulation_model=_FakeSimulationModel(),
        )

        # Act
        asyncio.run(
            use_case.execute(
                session_id="session-lane-001",
                run_id="run-lane-001",
                max_ticks=1,
                tick_interval_ms=0,
            )
        )
        persisted_tick = tick_repository.persisted_ticks[0]
        vehicle_payload = persisted_tick["snapshot"]["vehicles"][0]
        edge_payload = persisted_tick["snapshot"]["edges"]["('A', 'B', 0)"]

        # Assert
        assert (
            vehicle_payload.get("lane_index"),
            vehicle_payload.get("render_label"),
            edge_payload.get("n_lanes"),
        ) == (1, "BUS", 2)

    def test_replay_and_stream_ticks_when_replaying_history_keeps_lane_payload_fields_in_sse_data(
        self,
    ) -> None:
        """Replay serialization should keep lane metadata for reconnecting clients."""
        # Arrange
        tick_repository = _FakeTickRepository()
        tick_repository.append_tick(
            {
                "session_id": "session-lane-001",
                "run_id": "run-lane-001",
                "tick_number": 1,
                "snapshot": {
                    "vehicles": [{"id": 70, "lane_index": 1, "render_color": "#f39c12"}],
                    "edges": {
                        "('A', 'B', 0)": {
                            "n_lanes": 2,
                            "occupancy_cells_lane_major": [[0, 70, 0], [0, 0, 0]],
                        }
                    },
                },
                "metrics": {"tick": 1},
            }
        )
        use_case = ReplayAndStreamTicksUseCase(tick_repository=tick_repository)

        # Act
        stream = asyncio.run(
            use_case.execute(
                session_id="session-lane-001",
                run_id="run-lane-001",
                from_tick=-1,
                follow=False,
            )
        )
        payloads = asyncio.run(_collect_async_stream(stream=stream, limit=1))
        event_data = _extract_sse_data(payloads[0])

        # Assert
        assert (
            event_data["snapshot"]["vehicles"][0].get("lane_index"),
            event_data["snapshot"]["vehicles"][0].get("render_color"),
            event_data["snapshot"]["edges"]["('A', 'B', 0)"].get("n_lanes"),
        ) == (1, "#f39c12", 2)

    def test_replay_and_stream_ticks_when_last_event_id_is_used_keeps_lane_fields_and_cursor_progress(
        self,
    ) -> None:
        """Reconnect by cursor should preserve lane payload fields without replaying old ticks."""
        # Arrange
        tick_repository = _FakeTickRepository()
        tick_repository.append_tick(
            {
                "session_id": "session-lane-001",
                "run_id": "run-lane-001",
                "tick_number": 1,
                "snapshot": {
                    "vehicles": [{"id": 70, "lane_index": 0}],
                    "edges": {"('A', 'B', 0)": {"n_lanes": 2}},
                },
                "metrics": {"tick": 1},
            }
        )
        tick_repository.append_tick(
            {
                "session_id": "session-lane-001",
                "run_id": "run-lane-001",
                "tick_number": 2,
                "snapshot": {
                    "vehicles": [{"id": 71, "lane_index": 1, "lateral_offset_m": 1.75}],
                    "edges": {
                        "('A', 'B', 0)": {
                            "n_lanes": 2,
                            "occupancy_cells_lane_major": [[0, 0, 0], [0, 71, 0]],
                        }
                    },
                },
                "metrics": {"tick": 2},
            }
        )
        use_case = ReplayAndStreamTicksUseCase(tick_repository=tick_repository)

        # Act
        stream = asyncio.run(
            use_case.execute(
                session_id="session-lane-001",
                run_id="run-lane-001",
                from_tick=-1,
                last_event_id="1",
                follow=False,
            )
        )
        payloads = asyncio.run(_collect_async_stream(stream=stream, limit=1))
        event_data = _extract_sse_data(payloads[0])

        # Assert
        assert (
            event_data.get("tick_number"),
            event_data["snapshot"]["vehicles"][0].get("lane_index"),
            event_data["snapshot"]["edges"]["('A', 'B', 0)"].get("n_lanes"),
        ) == (2, 1, 2)

    def test_manager_backed_simulation_model_step_returns_lane_aware_snapshot_state(self) -> None:
        """Manager-backed adapter should expose lane payloads, not only tick counters."""
        # Arrange
        adapter = ManagerBackedSimulationModel(simulation_manager=_FakeSimulationManager())
        adapter.initialize_session(
            session_id="session-lane-001",
            simulation_parameters={"area": "Roma Norte", "config": {}},
        )

        # Act
        state, metrics, done = adapter.step()

        # Assert
        assert (
            "tick" in state,
            "vehicles" in state,
            "edges" in state,
            metrics.get("tick"),
            done,
        ) == (True, True, True, 1, False)
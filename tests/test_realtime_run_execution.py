"""Contract tests for realtime background execution orchestration."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import inspect
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pytest
from traffic_engine.infrastructure.runtime.manager_backed_simulation_model import (
    ManagerBackedSimulationModel,
)

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
    return asyncio.run(result) if inspect.isawaitable(result) else result


def _last_or_none(items: List[Any]) -> Any:
    return items[-1] if items else None


class _FakeSessionRepository:
    def __init__(self) -> None:
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.created_sessions: List[Dict[str, Any]] = []
        self.status_updates: List[Dict[str, Any]] = []
        self.latest_tick_updates: List[Dict[str, Any]] = []

    def create_session(self, session: Dict[str, Any]) -> Dict[str, Any]:
        self.sessions[session["session_id"]] = dict(session)
        self.created_sessions.append(dict(session))
        return dict(session)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self.sessions.get(session_id)
        return dict(session) if session else None

    def update_session_status(self, session_id: str, status: str, updated_at: datetime) -> None:
        self.status_updates.append(
            {
                "session_id": session_id,
                "status": status,
                "updated_at": updated_at,
            }
        )
        if session_id in self.sessions:
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
        self.latest_tick_updates.append(
            {
                "session_id": session_id,
                "run_id": run_id,
                "tick_number": tick_number,
                "latest_metrics": dict(latest_metrics),
                "updated_at": updated_at,
            }
        )
        if session_id in self.sessions:
            self.sessions[session_id]["latest_run_id"] = run_id
            self.sessions[session_id]["latest_tick"] = tick_number
            self.sessions[session_id]["latest_metrics"] = dict(latest_metrics)
            self.sessions[session_id]["updated_at"] = updated_at


class _FakeRunRepository:
    def __init__(self) -> None:
        self.runs: Dict[str, Dict[str, Any]] = {}
        self.created_runs: List[Dict[str, Any]] = []
        self.started_runs: List[str] = []
        self.completed_runs: List[str] = []
        self.failed_runs: List[str] = []

    def create_run(self, run: Dict[str, Any]) -> Dict[str, Any]:
        self.runs[run["run_id"]] = dict(run)
        self.created_runs.append(dict(run))
        return dict(run)

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        run = self.runs.get(run_id)
        return dict(run) if run else None

    def get_active_run_for_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        run = next(
            (
                run_item
                for run_item in self.runs.values()
                if run_item["session_id"] == session_id
                and run_item["status"] in {"queued", "running"}
            ),
            None,
        )
        return dict(run) if run else None

    def mark_run_started(self, run_id: str, started_at: datetime, worker_id: str) -> None:
        self.started_runs.append(run_id)
        if run_id in self.runs:
            self.runs[run_id]["status"] = "running"
            self.runs[run_id]["started_at"] = started_at
            self.runs[run_id]["runtime"]["worker_id"] = worker_id

    def mark_run_completed(self, run_id: str, completed_at: datetime) -> None:
        self.completed_runs.append(run_id)
        if run_id in self.runs:
            self.runs[run_id]["status"] = "completed"
            self.runs[run_id]["completed_at"] = completed_at

    def mark_run_failed(self, run_id: str, completed_at: datetime, error: Dict[str, Any]) -> None:
        self.failed_runs.append(run_id)
        if run_id in self.runs:
            self.runs[run_id]["status"] = "failed"
            self.runs[run_id]["completed_at"] = completed_at
            self.runs[run_id]["error"] = dict(error)


class _FakeTickRepository:
    def __init__(self, ordering_log: List[str]) -> None:
        self.ordering_log = ordering_log
        self.persisted_ticks: List[Dict[str, Any]] = []

    def append_tick(self, tick: Dict[str, Any]) -> Dict[str, Any]:
        self.persisted_ticks.append(dict(tick))
        self.ordering_log.append(f"persist:{tick['tick_number']}")
        return dict(tick)

    def list_ticks_after(
        self,
        session_id: str,
        run_id: str,
        from_tick: int,
        limit: int,
    ) -> List[Dict[str, Any]]:
        return []

    def get_latest_tick(self, session_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        return dict(self.persisted_ticks[-1]) if self.persisted_ticks else None


class _FakeTickStreamBroker:
    def __init__(self, ordering_log: List[str]) -> None:
        self.ordering_log = ordering_log
        self.published_events: List[Dict[str, Any]] = []

    def publish(self, run_id: str, event: Dict[str, Any]) -> None:
        self.published_events.append({"run_id": run_id, "event": dict(event)})
        self.ordering_log.append(f"publish:{event['tick_number']}")

    async def publish_tick(self, run_id: str, event: Dict[str, Any]) -> None:
        self.publish(run_id=run_id, event=event)

    async def publish_terminal_event(self, run_id: str, event: Dict[str, Any]) -> None:
        self.published_events.append({"run_id": run_id, "event": dict(event)})


class _FakeRunExecutor:
    def __init__(self) -> None:
        self.submissions: List[Dict[str, Any]] = []

    def submit(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        self.submissions.append({"args": args, "kwargs": kwargs})
        return {"accepted": True}

    def dispatch(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return self.submit(*args, **kwargs)

    def start(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return self.submit(*args, **kwargs)

    def start_run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return self.submit(*args, **kwargs)

    def schedule_run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return self.submit(*args, **kwargs)


class _FakeSimulationModel:
    def __init__(self) -> None:
        self._step_results: List[Tuple[Dict[str, Any], Dict[str, Any], bool]] = [
            ({"tick": 1}, {"tick": 1, "density": 0.2}, False),
            ({"tick": 2}, {"tick": 2, "density": 0.3}, True),
        ]

    def step(self) -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
        if not self._step_results:
            return {"tick": 2}, {"tick": 2, "density": 0.3}, True
        return self._step_results.pop(0)

    async def step_async(self) -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
        return self.step()


class _FakeCreateSimulationResponse:
    def __init__(self, simulation_id: str) -> None:
        self.success = True
        self.simulation_id = simulation_id
        self.error = ""


class _FakeStepSimulationResponse:
    def __init__(self, tick_number: int) -> None:
        self.success = True
        self.new_tick = tick_number
        self.metrics = {"tick": tick_number}
        self.error = ""


class _TrackingSimulationManager:
    def __init__(self) -> None:
        self.created_simulation_ids: List[str] = []
        self.step_simulation_ids: List[str] = []

    def create_simulation(self, request: Any) -> Any:
        simulation_id = f"sim-{len(self.created_simulation_ids) + 1}"
        self.created_simulation_ids.append(simulation_id)
        return _FakeCreateSimulationResponse(simulation_id=simulation_id)

    def step_simulation(self, simulation_id: str, request: Any) -> Any:
        self.step_simulation_ids.append(simulation_id)
        return _FakeStepSimulationResponse(tick_number=len(self.step_simulation_ids))

    def get_snapshot(self, simulation_id: str, request: Any) -> Any:
        return {
            "success": True,
            "snapshot": {"tick_owner_simulation_id": simulation_id},
        }


class TestRealtimeRunExecutionService:
    """Behavior tests for start/run realtime session orchestration."""

    def test_start_run_for_session_creates_metadata_and_dispatches_executor(
        self,
        realtime_symbol_loader,
        realtime_session_parameters,
    ) -> None:
        # Arrange
        use_case_cls = realtime_symbol_loader(
            "traffic_engine.application.use_cases.start_realtime_session",
            "StartRealtimeSessionUseCase",
        )
        session_repository = _FakeSessionRepository()
        run_repository = _FakeRunRepository()
        tick_repository = _FakeTickRepository(ordering_log=[])
        run_executor = _FakeRunExecutor()
        use_case = _instantiate_use_case(
            use_case_cls,
            {
                "session_repository": session_repository,
                "run_repository": run_repository,
                "tick_repository": tick_repository,
                "run_executor": run_executor,
                "executor": run_executor,
            },
        )
        request_payload = {
            "session_id": "session-realtime-001",
            "run_id": "run-realtime-001",
            "simulation_parameters": dict(realtime_session_parameters),
            "runtime": {"mode": "realtime", "tick_interval_ms": 250},
            "status": "pending",
        }

        # Act
        _invoke_use_case(
            use_case,
            ("execute", "start", "__call__"),
            request=request_payload,
            payload=request_payload,
            session_id=request_payload["session_id"],
            run_id=request_payload["run_id"],
            simulation_parameters=request_payload["simulation_parameters"],
            runtime=request_payload["runtime"],
        )

        # Assert
        assert (
            len(session_repository.created_sessions),
            len(run_repository.created_runs),
            len(run_executor.submissions),
        ) == (1, 1, 1)

    def test_background_run_persists_each_tick_before_publish(
        self,
        realtime_symbol_loader,
    ) -> None:
        # Arrange
        use_case_cls = realtime_symbol_loader(
            "traffic_engine.application.use_cases.run_realtime_session",
            "RunRealtimeSessionUseCase",
        )
        ordering_log: List[str] = []
        session_repository = _FakeSessionRepository()
        run_repository = _FakeRunRepository()
        tick_repository = _FakeTickRepository(ordering_log=ordering_log)
        stream_broker = _FakeTickStreamBroker(ordering_log=ordering_log)
        simulation_model = _FakeSimulationModel()

        now = datetime.now(timezone.utc)
        session_repository.create_session(
            {
                "session_id": "session-realtime-001",
                "created_at": now,
                "updated_at": now,
                "status": "pending",
                "simulation_parameters": {"initial_vehicles": 12},
            }
        )
        run_repository.create_run(
            {
                "run_id": "run-realtime-001",
                "session_id": "session-realtime-001",
                "created_at": now,
                "status": "queued",
                "runtime": {"mode": "realtime"},
            }
        )

        use_case = _instantiate_use_case(
            use_case_cls,
            {
                "session_repository": session_repository,
                "run_repository": run_repository,
                "tick_repository": tick_repository,
                "stream_broker": stream_broker,
                "tick_stream_broker": stream_broker,
                "simulation_model": simulation_model,
            },
        )

        # Act
        _invoke_use_case(
            use_case,
            ("execute", "run", "__call__"),
            session_id="session-realtime-001",
            run_id="run-realtime-001",
            max_ticks=2,
            tick_limit=2,
            tick_interval_ms=0,
            worker_id="test-worker",
        )

        # Assert
        assert ordering_log == [
            "persist:1",
            "publish:1",
            "persist:2",
            "publish:2",
        ]

    def test_background_run_updates_latest_status_and_handles_completion(
        self,
        realtime_symbol_loader,
    ) -> None:
        # Arrange
        use_case_cls = realtime_symbol_loader(
            "traffic_engine.application.use_cases.run_realtime_session",
            "RunRealtimeSessionUseCase",
        )
        ordering_log: List[str] = []
        session_repository = _FakeSessionRepository()
        run_repository = _FakeRunRepository()
        tick_repository = _FakeTickRepository(ordering_log=ordering_log)
        stream_broker = _FakeTickStreamBroker(ordering_log=ordering_log)
        simulation_model = _FakeSimulationModel()

        now = datetime.now(timezone.utc)
        session_repository.create_session(
            {
                "session_id": "session-realtime-001",
                "created_at": now,
                "updated_at": now,
                "status": "pending",
                "simulation_parameters": {"initial_vehicles": 12},
            }
        )
        run_repository.create_run(
            {
                "run_id": "run-realtime-001",
                "session_id": "session-realtime-001",
                "created_at": now,
                "status": "queued",
                "runtime": {"mode": "realtime"},
            }
        )

        use_case = _instantiate_use_case(
            use_case_cls,
            {
                "session_repository": session_repository,
                "run_repository": run_repository,
                "tick_repository": tick_repository,
                "stream_broker": stream_broker,
                "tick_stream_broker": stream_broker,
                "simulation_model": simulation_model,
            },
        )

        # Act
        _invoke_use_case(
            use_case,
            ("execute", "run", "__call__"),
            session_id="session-realtime-001",
            run_id="run-realtime-001",
            max_ticks=2,
            tick_limit=2,
            tick_interval_ms=0,
            worker_id="test-worker",
        )
        latest_update = _last_or_none(session_repository.latest_tick_updates)
        last_status = _last_or_none(session_repository.status_updates)

        # Assert
        assert (
            latest_update.get("tick_number") if latest_update else None,
            last_status.get("status") if last_status else None,
            _last_or_none(run_repository.completed_runs),
        ) == (2, "completed", "run-realtime-001")

    def test_terminal_run_status_event_uses_numeric_cursor_id(
        self,
        realtime_symbol_loader,
    ) -> None:
        # Arrange
        use_case_cls = realtime_symbol_loader(
            "traffic_engine.application.use_cases.run_realtime_session",
            "RunRealtimeSessionUseCase",
        )
        ordering_log: List[str] = []
        session_repository = _FakeSessionRepository()
        run_repository = _FakeRunRepository()
        tick_repository = _FakeTickRepository(ordering_log=ordering_log)
        stream_broker = _FakeTickStreamBroker(ordering_log=ordering_log)
        simulation_model = _FakeSimulationModel()

        now = datetime.now(timezone.utc)
        session_repository.create_session(
            {
                "session_id": "session-realtime-001",
                "created_at": now,
                "updated_at": now,
                "status": "pending",
                "simulation_parameters": {"initial_vehicles": 12},
            }
        )
        run_repository.create_run(
            {
                "run_id": "run-realtime-001",
                "session_id": "session-realtime-001",
                "created_at": now,
                "status": "queued",
                "runtime": {"mode": "realtime"},
            }
        )

        use_case = _instantiate_use_case(
            use_case_cls,
            {
                "session_repository": session_repository,
                "run_repository": run_repository,
                "tick_repository": tick_repository,
                "stream_broker": stream_broker,
                "tick_stream_broker": stream_broker,
                "simulation_model": simulation_model,
            },
        )

        # Act
        _invoke_use_case(
            use_case,
            ("execute", "run", "__call__"),
            session_id="session-realtime-001",
            run_id="run-realtime-001",
            max_ticks=2,
            tick_limit=2,
            tick_interval_ms=0,
            worker_id="test-worker",
        )
        terminal_event = _last_or_none(stream_broker.published_events)

        # Assert
        assert terminal_event == {
            "run_id": "run-realtime-001",
            "event": {
                "event": "run_status",
                "id": "2",
                "data": {
                    "session_id": "session-realtime-001",
                    "run_id": "run-realtime-001",
                    "status": "completed",
                    "error": None,
                },
            },
        }


class TestRealtimeRunExtensionService:
    """Behavior tests for extending a finished realtime session with a new run."""

    def test_extend_finished_session_creates_new_run_without_session_recreate_or_upsert(
        self,
        realtime_symbol_loader,
    ) -> None:
        # Arrange
        use_case_cls = realtime_symbol_loader(
            "traffic_engine.application.use_cases.extend_realtime_session",
            "ExtendRealtimeSessionUseCase",
        )

        class _TrackingSessionRepository(_FakeSessionRepository):
            def __init__(self) -> None:
                super().__init__()
                self.upsert_calls: List[Dict[str, Any]] = []

            def upsert_session(self, session: Dict[str, Any]) -> Dict[str, Any]:
                self.upsert_calls.append(dict(session))
                self.sessions[session["session_id"]] = dict(session)
                return dict(session)

        now = datetime.now(timezone.utc)
        session_repository = _TrackingSessionRepository()
        run_repository = _FakeRunRepository()
        tick_repository = _FakeTickRepository(ordering_log=[])
        run_executor = _FakeRunExecutor()

        session_repository.create_session(
            {
                "session_id": "session-finished-001",
                "created_at": now,
                "updated_at": now,
                "status": "completed",
                "simulation_parameters": {
                    "area": "Roma Norte, Ciudad de Mexico",
                    "max_ticks": 3,
                },
                "latest_run_id": "run-finished-001",
                "latest_tick": 3,
            }
        )
        run_repository.create_run(
            {
                "run_id": "run-finished-001",
                "session_id": "session-finished-001",
                "created_at": now,
                "status": "completed",
                "runtime": {"mode": "realtime", "max_ticks": 3},
                "completed_at": now,
            }
        )
        use_case = _instantiate_use_case(
            use_case_cls,
            {
                "session_repository": session_repository,
                "run_repository": run_repository,
                "tick_repository": tick_repository,
                "run_executor": run_executor,
                "executor": run_executor,
            },
        )

        # Act
        result = _invoke_use_case(
            use_case,
            ("execute", "extend", "__call__"),
            session_id="session-finished-001",
            n_steps=5,
            runtime={"tick_interval_ms": 0},
        )

        # Assert
        assert (
            len(session_repository.created_sessions),
            len(session_repository.upsert_calls),
            len(run_repository.created_runs),
            run_repository.created_runs[-1]["session_id"],
            result.get("session_id"),
            result.get("run_id") != "run-finished-001",
        ) == (
            1,
            0,
            2,
            "session-finished-001",
            "session-finished-001",
            True,
        )


class TestRealtimeRuntimeAdapterIsolation:
    """Regression contracts for realtime adapter session/run isolation."""

    def test_manager_backed_adapter_when_two_sessions_are_initialized_uses_distinct_simulation_ids(
        self,
    ) -> None:
        """Independent sessions should map to independent underlying simulation identifiers."""
        # Arrange
        simulation_manager = _TrackingSimulationManager()
        adapter = ManagerBackedSimulationModel(simulation_manager=simulation_manager)

        # Act
        adapter.initialize_session(
            session_id="session-realtime-001",
            simulation_parameters={"area": "Roma Norte", "config": {}},
        )
        first_state, _, _ = adapter.step()
        adapter.initialize_session(
            session_id="session-realtime-002",
            simulation_parameters={"area": "Condesa", "config": {}},
        )
        second_state, _, _ = adapter.step()

        # Assert
        assert (
            simulation_manager.created_simulation_ids,
            simulation_manager.step_simulation_ids,
            first_state.get("tick_owner_simulation_id"),
            second_state.get("tick_owner_simulation_id"),
        ) == (
            ["sim-1", "sim-2"],
            ["sim-1", "sim-2"],
            "sim-1",
            "sim-2",
        )

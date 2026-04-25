"""Contract tests for realtime persistence repositories.

These tests describe required behavior for session/run/tick persistence used by
realtime execution and reconnect recovery.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import importlib
import inspect
from typing import Any, Dict, List, Optional, Tuple

import pytest

class DuplicateTickError(RuntimeError):
    """Raised when duplicate tick writes are explicitly rejected."""


@dataclass
class _SessionRecord:
    session_id: str
    created_at: datetime
    updated_at: datetime
    status: str
    simulation_parameters: Dict[str, Any]
    latest_run_id: Optional[str] = None
    latest_tick: Optional[int] = None
    latest_metrics: Optional[Dict[str, Any]] = None


@dataclass
class _RunRecord:
    run_id: str
    session_id: str
    created_at: datetime
    status: str
    runtime: Dict[str, Any]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[Dict[str, Any]] = None


class _InMemorySessionRepository:
    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, session: Dict[str, Any]) -> Dict[str, Any]:
        self._sessions[session["session_id"]] = dict(session)
        return dict(session)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        return dict(session) if session else None

    def update_session_status(
        self,
        session_id: str,
        status: str,
        updated_at: datetime,
    ) -> None:
        self._sessions[session_id]["status"] = status
        self._sessions[session_id]["updated_at"] = updated_at

    def update_session_latest_tick(
        self,
        session_id: str,
        run_id: str,
        tick_number: int,
        latest_metrics: Dict[str, Any],
        updated_at: datetime,
    ) -> None:
        self._sessions[session_id]["latest_run_id"] = run_id
        self._sessions[session_id]["latest_tick"] = tick_number
        self._sessions[session_id]["latest_metrics"] = dict(latest_metrics)
        self._sessions[session_id]["updated_at"] = updated_at


class _InMemoryRunRepository:
    def __init__(self) -> None:
        self._runs: Dict[str, Dict[str, Any]] = {}

    def create_run(self, run: Dict[str, Any]) -> Dict[str, Any]:
        self._runs[run["run_id"]] = dict(run)
        return dict(run)

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        run = self._runs.get(run_id)
        return dict(run) if run else None

    def get_active_run_for_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        runs_for_session = [
            run
            for run in self._runs.values()
            if run["session_id"] == session_id and run["status"] in {"queued", "running"}
        ]
        runs_for_session.sort(key=lambda item: item["created_at"], reverse=True)
        return dict(runs_for_session[0]) if runs_for_session else None

    def mark_run_started(self, run_id: str, started_at: datetime, worker_id: str) -> None:
        self._runs[run_id]["status"] = "running"
        self._runs[run_id]["started_at"] = started_at
        self._runs[run_id]["runtime"]["worker_id"] = worker_id

    def mark_run_completed(self, run_id: str, completed_at: datetime) -> None:
        self._runs[run_id]["status"] = "completed"
        self._runs[run_id]["completed_at"] = completed_at

    def mark_run_failed(self, run_id: str, completed_at: datetime, error: Dict[str, Any]) -> None:
        self._runs[run_id]["status"] = "failed"
        self._runs[run_id]["completed_at"] = completed_at
        self._runs[run_id]["error"] = dict(error)


class _InMemoryTickRepository:
    def __init__(self, duplicate_mode: str = "rejected") -> None:
        self._duplicate_mode = duplicate_mode
        self._ticks: Dict[Tuple[str, int], Dict[str, Any]] = {}

    def append_tick(self, tick: Dict[str, Any]) -> Dict[str, Any]:
        key = (tick["run_id"], tick["tick_number"])
        if key in self._ticks:
            if self._duplicate_mode == "idempotent":
                return dict(self._ticks[key])
            raise DuplicateTickError("Duplicate run_id + tick_number.")
        self._ticks[key] = dict(tick)
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
            for tick in self._ticks.values()
            if tick["session_id"] == session_id
            and tick["run_id"] == run_id
            and tick["tick_number"] > from_tick
        ]
        matching.sort(key=lambda item: item["tick_number"])
        return [dict(item) for item in matching[:limit]]

    def get_latest_tick(self, session_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        run_ticks = [
            tick
            for tick in self._ticks.values()
            if tick["session_id"] == session_id and tick["run_id"] == run_id
        ]
        run_ticks.sort(key=lambda item: item["tick_number"], reverse=True)
        return dict(run_ticks[0]) if run_ticks else None


def _tick_numbers(ticks: List[Dict[str, Any]]) -> List[int]:
    return [tick["tick_number"] for tick in ticks]


def _duplicate_attempt_mode(
    repository: _InMemoryTickRepository,
    tick: Dict[str, Any],
) -> str:
    repository.append_tick(tick)
    try:
        repository.append_tick(tick)
        return "idempotent"
    except DuplicateTickError:
        return "rejected"


def _find_adapter_class(
    classes: List[type],
    expected_methods: set,
) -> Optional[type]:
    for class_candidate in classes:
        candidate_methods = set(dir(class_candidate))
        if expected_methods.issubset(candidate_methods):
            return class_candidate
    return None


class TestRealtimeRepositoryContracts:
    """Contract tests for repository behavior in realtime session persistence."""

    def test_realtime_persistence_contract_symbols_are_exported(
        self,
        realtime_symbol_loader,
    ) -> None:
        # Arrange / Act
        session_protocol = realtime_symbol_loader(
            "traffic_engine.application.contracts.realtime_persistence",
            "SimulationSessionRepository",
        )
        run_protocol = realtime_symbol_loader(
            "traffic_engine.application.contracts.realtime_persistence",
            "SimulationRunRepository",
        )
        tick_protocol = realtime_symbol_loader(
            "traffic_engine.application.contracts.realtime_persistence",
            "SimulationTickRepository",
        )

        # Assert
        assert (
            inspect.isclass(session_protocol)
            and inspect.isclass(run_protocol)
            and inspect.isclass(tick_protocol)
        )

    def test_session_repository_creates_session_metadata(self) -> None:
        # Arrange
        repository = _InMemorySessionRepository()
        now = datetime.now(timezone.utc)
        session = _SessionRecord(
            session_id="session-realtime-001",
            created_at=now,
            updated_at=now,
            status="pending",
            simulation_parameters={"initial_vehicles": 8},
        )

        # Act
        repository.create_session(session.__dict__)
        stored = repository.get_session("session-realtime-001")

        # Assert
        assert stored == session.__dict__

    def test_run_repository_creates_execution_record_for_session(self) -> None:
        # Arrange
        repository = _InMemoryRunRepository()
        now = datetime.now(timezone.utc)
        run = _RunRecord(
            run_id="run-realtime-001",
            session_id="session-realtime-001",
            created_at=now,
            status="queued",
            runtime={"mode": "realtime", "tick_interval_ms": 250},
        )

        # Act
        repository.create_run(run.__dict__)
        stored = repository.get_run("run-realtime-001")

        # Assert
        assert stored == run.__dict__

    def test_tick_repository_persists_ticks_separately_from_session_metadata(self) -> None:
        # Arrange
        session_repository = _InMemorySessionRepository()
        tick_repository = _InMemoryTickRepository()
        now = datetime.now(timezone.utc)

        session_repository.create_session(
            _SessionRecord(
                session_id="session-realtime-001",
                created_at=now,
                updated_at=now,
                status="running",
                simulation_parameters={"initial_vehicles": 10},
            ).__dict__
        )

        tick_document = {
            "session_id": "session-realtime-001",
            "run_id": "run-realtime-001",
            "tick_number": 1,
            "recorded_at": now,
            "metrics": {"density": 0.25},
            "snapshot": {"vehicles": 10},
            "events": [],
        }

        # Act
        tick_repository.append_tick(tick_document)
        stored_session = session_repository.get_session("session-realtime-001")
        stored_ticks = tick_repository.list_ticks_after(
            session_id="session-realtime-001",
            run_id="run-realtime-001",
            from_tick=-1,
            limit=10,
        )

        # Assert
        assert (
            ("ticks" in stored_session),
            ("tick_history" in stored_session),
            stored_ticks,
        ) == (False, False, [tick_document])

    def test_tick_repository_lists_ticks_after_from_tick_in_ascending_order(self) -> None:
        # Arrange
        repository = _InMemoryTickRepository()
        now = datetime.now(timezone.utc)
        tick_3 = {
            "session_id": "session-realtime-001",
            "run_id": "run-realtime-001",
            "tick_number": 3,
            "recorded_at": now,
            "metrics": {"density": 0.4},
        }
        tick_1 = {
            "session_id": "session-realtime-001",
            "run_id": "run-realtime-001",
            "tick_number": 1,
            "recorded_at": now,
            "metrics": {"density": 0.2},
        }
        tick_2 = {
            "session_id": "session-realtime-001",
            "run_id": "run-realtime-001",
            "tick_number": 2,
            "recorded_at": now,
            "metrics": {"density": 0.3},
        }

        # Act
        repository.append_tick(tick_3)
        repository.append_tick(tick_1)
        repository.append_tick(tick_2)
        ordered = repository.list_ticks_after(
            session_id="session-realtime-001",
            run_id="run-realtime-001",
            from_tick=1,
            limit=10,
        )

        # Assert
        assert _tick_numbers(ordered) == [2, 3]

    @pytest.mark.parametrize("duplicate_mode", ["idempotent", "rejected"])
    def test_duplicate_tick_write_is_idempotent_or_rejected_consistently(
        self,
        duplicate_mode: str,
    ) -> None:
        # Arrange
        tick = {
            "session_id": "session-realtime-001",
            "run_id": "run-realtime-001",
            "tick_number": 7,
            "recorded_at": datetime.now(timezone.utc),
            "metrics": {"density": 0.5},
        }
        first_repository = _InMemoryTickRepository(duplicate_mode=duplicate_mode)
        second_repository = _InMemoryTickRepository(duplicate_mode=duplicate_mode)

        # Act
        first_mode = _duplicate_attempt_mode(first_repository, tick)
        second_mode = _duplicate_attempt_mode(second_repository, tick)
        surviving_ticks = first_repository.list_ticks_after(
            session_id="session-realtime-001",
            run_id="run-realtime-001",
            from_tick=-1,
            limit=10,
        )

        # Assert
        assert (first_mode, second_mode, len(surviving_ticks)) == (
            duplicate_mode,
            duplicate_mode,
            1,
        )

    def test_mongo_realtime_repository_module_exposes_session_run_tick_adapters(self) -> None:
        # Arrange
        module_name = "traffic_engine.infrastructure.persistence.mongo_realtime_repositories"

        # Act
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            pytest.fail(
                "Missing infrastructure module "
                f"'{module_name}'. Implement Mongo realtime repository adapters."
            )

        classes = [value for value in vars(module).values() if inspect.isclass(value)]
        session_adapter = _find_adapter_class(
            classes,
            {
                "create_session",
                "get_session",
                "update_session_status",
                "update_session_latest_tick",
            },
        )
        run_adapter = _find_adapter_class(
            classes,
            {
                "create_run",
                "get_run",
                "get_active_run_for_session",
                "mark_run_started",
                "mark_run_completed",
                "mark_run_failed",
            },
        )
        tick_adapter = _find_adapter_class(
            classes,
            {
                "append_tick",
                "list_ticks_after",
                "get_latest_tick",
            },
        )

        # Assert
        assert session_adapter and run_adapter and tick_adapter

"""Use case for creating and dispatching realtime simulation sessions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from ..contracts.realtime_entities import RealtimeRunRecord, RealtimeSessionRecord, RunStatus, SessionStatus
from ..contracts.realtime_persistence import (
    SimulationRunRepository,
    SimulationSessionRepository,
    SimulationTickRepository,
)
from ..contracts.realtime_runtime import RunExecutor


class StartRealtimeSessionUseCase:
    """Create realtime session metadata and schedule background execution."""

    def __init__(
        self,
        session_repository: SimulationSessionRepository,
        run_repository: SimulationRunRepository,
        tick_repository: Optional[SimulationTickRepository] = None,
        run_executor: Optional[RunExecutor] = None,
        executor: Optional[RunExecutor] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        """Initialize the use case dependencies.

        Args:
            session_repository: Session metadata repository.
            run_repository: Run metadata repository.
            tick_repository: Unused here but accepted for test-friendly composition.
            run_executor: Preferred background run executor.
            executor: Backward-compatible alias for the executor.
            clock: Optional UTC clock provider.
        """
        self.session_repository = session_repository
        self.run_repository = run_repository
        self.tick_repository = tick_repository
        self.run_executor = run_executor or executor
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def execute(
        self,
        request: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        run_id: Optional[str] = None,
        simulation_parameters: Optional[Dict[str, Any]] = None,
        runtime: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Persist session and run metadata, then dispatch execution."""
        payload = dict(request or {})
        resolved_session_id = session_id or payload.get("session_id") or str(uuid4())
        resolved_run_id = run_id or payload.get("run_id") or str(uuid4())
        resolved_parameters = dict(simulation_parameters or payload.get("simulation_parameters") or {})
        resolved_runtime = dict(runtime or payload.get("runtime") or {})
        now = self.clock()

        active_run = self.run_repository.get_active_run_for_session(resolved_session_id)
        if active_run:
            raise ValueError(f"Session {resolved_session_id} already has an active run.")
        if self.run_executor is None:
            raise RuntimeError("A run executor is required for realtime session startup.")

        session_record = RealtimeSessionRecord(
            session_id=resolved_session_id,
            created_at=now,
            updated_at=now,
            status=payload.get("status", SessionStatus.PENDING.value),
            simulation_parameters=resolved_parameters,
            latest_run_id=resolved_run_id,
        )
        run_record = RealtimeRunRecord(
            run_id=resolved_run_id,
            session_id=resolved_session_id,
            created_at=now,
            status=RunStatus.QUEUED.value,
            runtime=resolved_runtime,
            parameters_snapshot=resolved_parameters,
        )

        self.session_repository.create_session(session_record.to_document())
        self.run_repository.create_run(run_record.to_document())
        dispatch_result = self.run_executor.submit(
            session_id=resolved_session_id,
            run_id=resolved_run_id,
            simulation_parameters=resolved_parameters,
            runtime=resolved_runtime,
        )

        return {
            "session_id": resolved_session_id,
            "run_id": resolved_run_id,
            "status": run_record.status,
            "dispatch": dispatch_result,
        }
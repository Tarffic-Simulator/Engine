"""Use case for extending a finished realtime session with a new execution run."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from ..contracts.realtime_entities import (
    RealtimeRunRecord,
    RunStatus,
    SessionStatus,
    is_active_public_status,
    normalize_public_status,
)
from ..contracts.realtime_persistence import (
    SimulationRunRepository,
    SimulationSessionRepository,
    SimulationTickRepository,
)
from ..contracts.realtime_runtime import RunExecutor


class ExtendRealtimeSessionUseCase:
    """Create and dispatch a new run for an existing finished realtime session.

    Args:
        session_repository: Repository used to read and update session metadata.
        run_repository: Repository used to read and create run metadata.
        tick_repository: Accepted for consistent composition with related use cases.
        run_executor: Preferred background run executor.
        executor: Backward-compatible alias for the run executor.
        clock: Optional UTC clock provider.
    """

    def __init__(
        self,
        session_repository: SimulationSessionRepository,
        run_repository: SimulationRunRepository,
        tick_repository: Optional[SimulationTickRepository] = None,
        run_executor: Optional[RunExecutor] = None,
        executor: Optional[RunExecutor] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        """Initialize extension dependencies.

        Args:
            session_repository: Repository used to read and update session metadata.
            run_repository: Repository used to read and create run metadata.
            tick_repository: Accepted for consistent composition with related use cases.
            run_executor: Preferred background run executor.
            executor: Backward-compatible alias for the run executor.
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
        n_steps: Optional[int] = None,
        runtime: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new run for a finished session and dispatch it in background.

        Args:
            request: Optional dictionary payload for compatibility with wrapper callers.
            session_id: Session identifier to extend.
            n_steps: Additional ticks to execute in the new run.
            runtime: Optional runtime overrides.
            run_id: Optional client-supplied run identifier.

        Returns:
            Dictionary containing the new run identifiers and lifecycle metadata.

        Raises:
            ValueError: If the session does not exist, is not finished, or has an active run.
            RuntimeError: If no executor is configured.
        """
        payload = dict(request or {})
        resolved_session_id = session_id or payload.get("session_id")
        if not resolved_session_id:
            raise ValueError("A session_id is required to extend a realtime session.")

        resolved_n_steps = int(n_steps or payload.get("n_steps") or 0)
        if resolved_n_steps < 1:
            raise ValueError("n_steps must be greater than or equal to 1.")

        if self.run_executor is None:
            raise RuntimeError("A run executor is required for realtime session extension.")

        session = self.session_repository.get_session(resolved_session_id)
        if session is None:
            raise ValueError(f"Unknown realtime session '{resolved_session_id}'.")

        public_session_status = normalize_public_status(session.get("status"))
        if public_session_status != "finished":
            raise ValueError(
                f"Realtime session '{resolved_session_id}' must be finished before it can be extended."
            )

        active_run = self.run_repository.get_active_run_for_session(resolved_session_id)
        if active_run is not None:
            raise ValueError(f"Session {resolved_session_id} already has an active run.")

        if hasattr(self.run_repository, "list_runs_for_session"):
            latest_runs = self.run_repository.list_runs_for_session(resolved_session_id, limit=1)
            if latest_runs and is_active_public_status(latest_runs[0].get("status")):
                raise ValueError(f"Session {resolved_session_id} already has an active run.")

        now = self.clock()
        latest_run_id = session.get("latest_run_id")
        latest_run = self.run_repository.get_run(latest_run_id) if latest_run_id else None
        resolved_run_id = run_id or payload.get("run_id") or str(uuid4())

        base_runtime = dict(latest_run.get("runtime") or {}) if isinstance(latest_run, dict) else {}
        override_runtime = dict(runtime or payload.get("runtime") or {})
        merged_runtime = {**base_runtime, **override_runtime}
        merged_runtime.setdefault("mode", "realtime")
        merged_runtime["max_ticks"] = resolved_n_steps

        run_record = RealtimeRunRecord(
            run_id=resolved_run_id,
            session_id=resolved_session_id,
            created_at=now,
            status=RunStatus.QUEUED.value,
            runtime=merged_runtime,
            parameters_snapshot=dict(session.get("simulation_parameters") or {}),
        )

        self.session_repository.update_session_status(
            resolved_session_id,
            SessionStatus.PENDING.value,
            now,
        )
        self.run_repository.create_run(run_record.to_document())
        dispatch_result = self.run_executor.submit(
            session_id=resolved_session_id,
            run_id=resolved_run_id,
            simulation_parameters=dict(session.get("simulation_parameters") or {}),
            runtime=merged_runtime,
        )

        return {
            "session_id": resolved_session_id,
            "run_id": resolved_run_id,
            "session_status": SessionStatus.PENDING.value,
            "run_status": run_record.status,
            "status": run_record.status,
            "dispatch": dispatch_result,
        }
"""Persistence contracts for realtime simulation sessions."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol


class SimulationSessionRepository(Protocol):
    """Repository contract for realtime session metadata."""

    def create_session(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a new realtime session document."""

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return a session document by identifier."""

    def update_session_status(self, session_id: str, status: str, updated_at: datetime) -> None:
        """Update the lifecycle status for a session."""

    def update_session_latest_tick(
        self,
        session_id: str,
        run_id: str,
        tick_number: int,
        latest_metrics: Dict[str, Any],
        updated_at: datetime,
    ) -> None:
        """Update the latest replay metadata for a session."""


class SimulationRunRepository(Protocol):
    """Repository contract for execution attempts tied to sessions."""

    def create_run(self, run: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a new run document."""

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Return a run document by identifier."""

    def get_active_run_for_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return the active queued or running run for a session, if any."""

    def mark_run_started(self, run_id: str, started_at: datetime, worker_id: str) -> None:
        """Mark a run as started by a worker."""

    def mark_run_completed(self, run_id: str, completed_at: datetime) -> None:
        """Mark a run as completed."""

    def mark_run_failed(self, run_id: str, completed_at: datetime, error: Dict[str, Any]) -> None:
        """Mark a run as failed with structured error data."""


class SimulationTickRepository(Protocol):
    """Repository contract for immutable tick history."""

    def append_tick(self, tick: Dict[str, Any]) -> Dict[str, Any]:
        """Persist one tick document."""

    def list_ticks_after(
        self,
        session_id: str,
        run_id: str,
        from_tick: int,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """List persisted ticks with tick_number strictly greater than from_tick."""

    def get_latest_tick(self, session_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        """Return the most recent tick for one run."""
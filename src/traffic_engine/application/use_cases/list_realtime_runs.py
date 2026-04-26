"""Use case for listing persisted realtime runs."""

from __future__ import annotations

from typing import Any, Dict, List

from ..contracts.realtime_persistence import SimulationRunRepository


class ListRealtimeRunsUseCase:
    """List persisted realtime runs for one session.

    Args:
        run_repository: Repository used to read persisted run metadata.
    """

    def __init__(self, run_repository: SimulationRunRepository) -> None:
        """Initialize the use case dependencies.

        Args:
            run_repository: Repository used to read persisted run metadata.
        """
        self.run_repository = run_repository

    def execute(self, session_id: str, limit: int = 50) -> Dict[str, Any]:
        """Return a bounded list of runs for one persisted session.

        Args:
            session_id: Session identifier.
            limit: Maximum number of runs to return.

        Returns:
            Dictionary with run summaries and count.
        """
        runs: List[Dict[str, Any]] = self.run_repository.list_runs_for_session(
            session_id=session_id,
            limit=limit,
        )
        return {"runs": runs, "count": len(runs)}
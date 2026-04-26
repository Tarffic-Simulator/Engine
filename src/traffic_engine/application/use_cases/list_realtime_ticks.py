"""Use case for listing persisted realtime ticks."""

from __future__ import annotations

from typing import Any, Dict, List

from ..contracts.realtime_persistence import SimulationTickRepository


class ListRealtimeTicksUseCase:
    """List persisted realtime ticks for external client replay.

    Args:
        tick_repository: Repository used to read immutable tick history.
    """

    def __init__(self, tick_repository: SimulationTickRepository) -> None:
        """Initialize the use case dependencies.

        Args:
            tick_repository: Repository used to read immutable tick history.
        """
        self.tick_repository = tick_repository

    def execute(
        self,
        session_id: str,
        run_id: str,
        from_tick: int = -1,
        limit: int = 200,
    ) -> Dict[str, Any]:
        """Return a bounded tick window in ascending persisted tick order.

        Args:
            session_id: Session identifier.
            run_id: Run identifier.
            from_tick: Exclusive lower tick boundary.
            limit: Maximum number of ticks to return.

        Returns:
            Dictionary with persisted ticks and count.
        """
        ticks: List[Dict[str, Any]] = self.tick_repository.list_ticks_after(
            session_id=session_id,
            run_id=run_id,
            from_tick=from_tick,
            limit=limit,
        )
        return {"ticks": ticks, "count": len(ticks)}
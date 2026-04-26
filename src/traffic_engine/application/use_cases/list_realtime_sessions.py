"""Use case for listing persisted realtime sessions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..contracts.realtime_entities import internal_session_status_for_public
from ..contracts.realtime_persistence import SimulationSessionRepository


class ListRealtimeSessionsUseCase:
    """List persisted realtime sessions for external client replay browsing.

    Args:
        session_repository: Repository used to read persisted session metadata.
    """

    def __init__(self, session_repository: SimulationSessionRepository) -> None:
        """Initialize the use case dependencies.

        Args:
            session_repository: Repository used to read persisted session metadata.
        """
        self.session_repository = session_repository

    def execute(self, status: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        """Return a bounded list of persisted realtime sessions.

        Args:
            status: Optional lifecycle status filter.
            limit: Maximum number of sessions to return.

        Returns:
            Dictionary with session summaries and count.
        """
        sessions: List[Dict[str, Any]] = self.session_repository.list_sessions(
            status=internal_session_status_for_public(status),
            limit=limit,
        )
        return {"sessions": sessions, "count": len(sessions)}
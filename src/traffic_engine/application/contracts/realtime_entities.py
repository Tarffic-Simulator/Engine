"""Application-layer entities for realtime simulation sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class SessionStatus(str, Enum):
    """Lifecycle states for a persisted realtime session."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunStatus(str, Enum):
    """Lifecycle states for a persisted realtime execution run."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class RealtimeSessionRecord:
    """Stored metadata for a realtime simulation session.

    Attributes:
        session_id: Stable public identifier.
        created_at: Session creation timestamp in UTC.
        updated_at: Last metadata update timestamp in UTC.
        status: Current session lifecycle state.
        simulation_parameters: Client-supplied normalized simulation parameters.
        latest_run_id: Most recent execution identifier, if available.
        latest_tick: Highest persisted tick number, if available.
        latest_metrics: Most recent compact metrics snapshot, if available.
    """

    session_id: str
    created_at: datetime
    updated_at: datetime
    status: str
    simulation_parameters: Dict[str, Any]
    latest_run_id: Optional[str] = None
    latest_tick: Optional[int] = None
    latest_metrics: Optional[Dict[str, Any]] = None

    def to_document(self) -> Dict[str, Any]:
        """Return a Mongo-friendly dictionary representation."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "simulation_parameters": dict(self.simulation_parameters),
            "latest_run_id": self.latest_run_id,
            "latest_tick": self.latest_tick,
            "latest_metrics": dict(self.latest_metrics or {}) or None,
        }


@dataclass(frozen=True)
class RealtimeRunRecord:
    """Stored metadata for an execution run tied to one session."""

    run_id: str
    session_id: str
    created_at: datetime
    status: str
    runtime: Dict[str, Any]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    parameters_snapshot: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    def to_document(self) -> Dict[str, Any]:
        """Return a Mongo-friendly dictionary representation."""
        return {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "status": self.status,
            "runtime": dict(self.runtime),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "parameters_snapshot": dict(self.parameters_snapshot or {}) or None,
            "error": dict(self.error or {}) or None,
        }


@dataclass(frozen=True)
class RealtimeTickRecord:
    """Immutable tick history record used for replay and live streaming."""

    session_id: str
    run_id: str
    tick_number: int
    recorded_at: datetime
    metrics: Dict[str, Any]
    snapshot: Optional[Dict[str, Any]] = None
    events: list[Dict[str, Any]] = field(default_factory=list)

    def to_document(self) -> Dict[str, Any]:
        """Return a Mongo-friendly dictionary representation."""
        return {
            "session_id": self.session_id,
            "run_id": self.run_id,
            "tick_number": self.tick_number,
            "recorded_at": self.recorded_at,
            "metrics": dict(self.metrics),
            "snapshot": dict(self.snapshot or {}) or None,
            "events": [dict(event) for event in self.events],
        }
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


class PublicLifecycleStatus(str, Enum):
    """Canonical lifecycle states exposed by the public realtime contract."""

    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELLED = "cancelled"


_PUBLIC_STATUS_BY_INTERNAL_VALUE: Dict[str, str] = {
    SessionStatus.PENDING.value: PublicLifecycleStatus.PENDING.value,
    SessionStatus.RUNNING.value: PublicLifecycleStatus.RUNNING.value,
    SessionStatus.PAUSED.value: PublicLifecycleStatus.RUNNING.value,
    SessionStatus.COMPLETED.value: PublicLifecycleStatus.FINISHED.value,
    SessionStatus.FAILED.value: PublicLifecycleStatus.FAILED.value,
    SessionStatus.CANCELLED.value: PublicLifecycleStatus.CANCELLED.value,
    RunStatus.QUEUED.value: PublicLifecycleStatus.PENDING.value,
    RunStatus.RUNNING.value: PublicLifecycleStatus.RUNNING.value,
    RunStatus.COMPLETED.value: PublicLifecycleStatus.FINISHED.value,
    RunStatus.FAILED.value: PublicLifecycleStatus.FAILED.value,
    RunStatus.CANCELLED.value: PublicLifecycleStatus.CANCELLED.value,
    PublicLifecycleStatus.PENDING.value: PublicLifecycleStatus.PENDING.value,
    PublicLifecycleStatus.RUNNING.value: PublicLifecycleStatus.RUNNING.value,
    PublicLifecycleStatus.FINISHED.value: PublicLifecycleStatus.FINISHED.value,
    PublicLifecycleStatus.FAILED.value: PublicLifecycleStatus.FAILED.value,
    PublicLifecycleStatus.CANCELLED.value: PublicLifecycleStatus.CANCELLED.value,
    "canceled": PublicLifecycleStatus.CANCELLED.value,
}

_INTERNAL_SESSION_STATUS_BY_PUBLIC_VALUE: Dict[str, str] = {
    PublicLifecycleStatus.PENDING.value: SessionStatus.PENDING.value,
    PublicLifecycleStatus.RUNNING.value: SessionStatus.RUNNING.value,
    PublicLifecycleStatus.FINISHED.value: SessionStatus.COMPLETED.value,
    PublicLifecycleStatus.FAILED.value: SessionStatus.FAILED.value,
    PublicLifecycleStatus.CANCELLED.value: SessionStatus.CANCELLED.value,
}

_INTERNAL_RUN_STATUS_BY_PUBLIC_VALUE: Dict[str, str] = {
    PublicLifecycleStatus.PENDING.value: RunStatus.QUEUED.value,
    PublicLifecycleStatus.RUNNING.value: RunStatus.RUNNING.value,
    PublicLifecycleStatus.FINISHED.value: RunStatus.COMPLETED.value,
    PublicLifecycleStatus.FAILED.value: RunStatus.FAILED.value,
    PublicLifecycleStatus.CANCELLED.value: RunStatus.CANCELLED.value,
}

_ACTIVE_PUBLIC_STATUSES = {
    PublicLifecycleStatus.PENDING.value,
    PublicLifecycleStatus.RUNNING.value,
}

_TERMINAL_PUBLIC_STATUSES = {
    PublicLifecycleStatus.FINISHED.value,
    PublicLifecycleStatus.FAILED.value,
    PublicLifecycleStatus.CANCELLED.value,
}


def normalize_public_status(status: Any) -> str:
    """Normalize an internal or public lifecycle value to the canonical public form.

    Args:
        status: Raw lifecycle value from persistence or transport boundaries.

    Returns:
        Canonical public lifecycle vocabulary when recognized.
    """
    if isinstance(status, Enum):
        raw_value = status.value
    else:
        raw_value = str(status or "").strip().lower()

    if not raw_value:
        return raw_value

    return _PUBLIC_STATUS_BY_INTERNAL_VALUE.get(raw_value, raw_value)


def internal_session_status_for_public(status: Optional[str]) -> Optional[str]:
    """Map a public session status filter to the persisted session value.

    Args:
        status: Optional public lifecycle value.

    Returns:
        Persisted session lifecycle value, or ``None`` when no filter is supplied.
    """
    if status is None:
        return None

    normalized_status = normalize_public_status(status)
    return _INTERNAL_SESSION_STATUS_BY_PUBLIC_VALUE.get(normalized_status, str(status).strip().lower())


def internal_run_status_for_public(status: Optional[str]) -> Optional[str]:
    """Map a public run status filter to the persisted run value.

    Args:
        status: Optional public lifecycle value.

    Returns:
        Persisted run lifecycle value, or ``None`` when no filter is supplied.
    """
    if status is None:
        return None

    normalized_status = normalize_public_status(status)
    return _INTERNAL_RUN_STATUS_BY_PUBLIC_VALUE.get(normalized_status, str(status).strip().lower())


def is_active_public_status(status: Any) -> bool:
    """Return whether a lifecycle value represents an active run/session.

    Args:
        status: Raw lifecycle value.

    Returns:
        ``True`` when the normalized public status is pending or running.
    """
    return normalize_public_status(status) in _ACTIVE_PUBLIC_STATUSES


def is_terminal_public_status(status: Any) -> bool:
    """Return whether a lifecycle value is terminal in the public contract.

    Args:
        status: Raw lifecycle value.

    Returns:
        ``True`` when the normalized public status is finished, failed, or cancelled.
    """
    return normalize_public_status(status) in _TERMINAL_PUBLIC_STATUSES


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
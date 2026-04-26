"""Pydantic response models for realtime session endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, validator

from ...application.contracts.realtime_entities import PublicLifecycleStatus, normalize_public_status


PUBLIC_LIFECYCLE_VALUES: Tuple[str, ...] = tuple(
    status.value for status in PublicLifecycleStatus
)


class CreateRealtimeSessionResponse(BaseModel):
    """Response payload returned after creating a realtime session."""

    session_id: str = Field(description="Stable realtime session identifier.")
    run_id: str = Field(description="Execution run identifier.")
    session_status: str = Field(
        description="Canonical public session lifecycle status.",
        enum=PUBLIC_LIFECYCLE_VALUES,
    )
    run_status: str = Field(
        description="Canonical public run lifecycle status.",
        enum=PUBLIC_LIFECYCLE_VALUES,
    )
    status: str = Field(
        description="Temporary alias of run_status.",
        enum=PUBLIC_LIFECYCLE_VALUES,
    )
    websocket_url: str = Field(description="Canonical WebSocket URL for replay and live follow.")
    stream_url: Optional[str] = Field(default=None, description="Convenience URL for SSE reconnects.")

    @validator("session_status", "run_status", "status", pre=True)
    def normalize_status_fields(cls, value: Any) -> str:
        """Normalize internal lifecycle values to the public contract."""
        return normalize_public_status(value)


class RealtimeAvailabilityResponse(BaseModel):
    """Response payload for realtime persistence availability."""

    available: bool = Field(description="Whether realtime persistence services can be used.")
    status: str = Field(description="Public availability status for realtime persistence.")
    message: str = Field(description="Client-safe explanation of the current realtime state.")


class RealtimeSessionSummaryResponse(BaseModel):
    """Summary payload for one persisted realtime session."""

    session_id: str = Field(description="Stable realtime session identifier.")
    created_at: datetime = Field(description="Session creation timestamp.")
    updated_at: datetime = Field(description="Last update timestamp.")
    status: str = Field(description="Current lifecycle status.", enum=PUBLIC_LIFECYCLE_VALUES)
    simulation_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Simulation parameters persisted with the session.",
    )
    latest_run_id: Optional[str] = Field(default=None, description="Most recent run identifier.")
    latest_tick: Optional[int] = Field(default=None, description="Latest persisted tick number.")
    latest_metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Most recent persisted metrics summary.",
    )

    @validator("status", pre=True)
    def normalize_status(cls, value: Any) -> str:
        """Normalize internal session statuses for public responses."""
        return normalize_public_status(value)


class ListRealtimeSessionsResponse(BaseModel):
    """Response payload for the persisted realtime session catalog."""

    sessions: List[RealtimeSessionSummaryResponse] = Field(
        default_factory=list,
        description="Bounded list of persisted realtime sessions.",
    )
    count: int = Field(description="Number of returned sessions.")


class RealtimeRunSummaryResponse(BaseModel):
    """Summary payload for one persisted realtime run."""

    run_id: str = Field(description="Execution run identifier.")
    session_id: str = Field(description="Parent realtime session identifier.")
    created_at: datetime = Field(description="Run creation timestamp.")
    status: str = Field(description="Current lifecycle status.", enum=PUBLIC_LIFECYCLE_VALUES)
    runtime: Dict[str, Any] = Field(default_factory=dict, description="Persisted runtime configuration.")
    started_at: Optional[datetime] = Field(default=None, description="Run start timestamp.")
    completed_at: Optional[datetime] = Field(default=None, description="Run completion timestamp.")
    error: Optional[Dict[str, Any]] = Field(default=None, description="Structured terminal error payload.")
    parameters_snapshot: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Simulation parameters captured at run creation.",
    )

    @validator("status", pre=True)
    def normalize_status(cls, value: Any) -> str:
        """Normalize internal run statuses for public responses."""
        return normalize_public_status(value)


class ListRealtimeRunsResponse(BaseModel):
    """Response payload for the persisted run catalog of one session."""

    runs: List[RealtimeRunSummaryResponse] = Field(
        default_factory=list,
        description="Bounded list of runs for one session.",
    )
    count: int = Field(description="Number of returned runs.")


class RealtimeTickResponse(BaseModel):
    """Payload for one persisted realtime tick document."""

    session_id: str = Field(description="Parent realtime session identifier.")
    run_id: str = Field(description="Execution run identifier.")
    tick_number: int = Field(description="Persisted tick number.")
    recorded_at: Optional[datetime] = Field(default=None, description="Tick persistence timestamp.")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Metrics captured for this tick.")
    snapshot: Optional[Dict[str, Any]] = Field(default=None, description="Visualization snapshot captured for this tick.")
    events: List[Dict[str, Any]] = Field(default_factory=list, description="Structured events emitted for this tick.")


class ListRealtimeTicksResponse(BaseModel):
    """Response payload for one persisted realtime tick window."""

    ticks: List[RealtimeTickResponse] = Field(
        default_factory=list,
        description="Ticks ordered by ascending tick number.",
    )
    count: int = Field(description="Number of returned ticks.")
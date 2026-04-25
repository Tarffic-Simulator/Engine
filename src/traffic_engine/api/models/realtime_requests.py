"""Pydantic request models for realtime session endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, root_validator, validator


class RealtimeRuntimeConfig(BaseModel):
    """Runtime configuration for background realtime execution."""

    mode: str = Field(default="realtime", description="Execution mode for the run.")
    tick_interval_ms: int = Field(default=250, ge=0, description="Delay between ticks in milliseconds.")
    max_ticks: int = Field(default=100, ge=1, description="Maximum number of ticks for the run.")


class CreateRealtimeSessionRequest(BaseModel):
    """Request body for creating a realtime simulation session."""

    session_id: Optional[str] = Field(default=None, description="Optional client-supplied session identifier.")
    run_id: Optional[str] = Field(default=None, description="Optional client-supplied run identifier.")
    area: Optional[str] = Field(default=None, description="Named geographic area for simulation setup.")
    bbox: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional bounding box with min_x, max_x, min_y, and max_y.",
    )
    config: Dict[str, Any] = Field(default_factory=dict, description="Simulation configuration overrides.")
    runtime: RealtimeRuntimeConfig = Field(default_factory=RealtimeRuntimeConfig)

    @root_validator(skip_on_failure=True)
    def validate_location_source(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Require either an area or a bbox for simulation initialization."""
        if not values.get("area") and not values.get("bbox"):
            raise ValueError("Either area or bbox must be provided.")
        return values

    @validator("bbox")
    def validate_bbox(cls, value: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
        """Validate bbox coordinate ordering when present."""
        if value is None:
            return value
        required_keys = {"min_x", "max_x", "min_y", "max_y"}
        if not required_keys.issubset(value.keys()):
            raise ValueError(f"bbox must contain keys {sorted(required_keys)}")
        if value["min_x"] >= value["max_x"] or value["min_y"] >= value["max_y"]:
            raise ValueError("bbox min values must be less than max values")
        return value

    def to_simulation_parameters(self) -> Dict[str, Any]:
        """Return normalized parameters persisted for session recovery."""
        return {
            "area": self.area,
            "bbox": dict(self.bbox) if self.bbox else None,
            "config": dict(self.config),
            "max_ticks": self.runtime.max_ticks,
        }
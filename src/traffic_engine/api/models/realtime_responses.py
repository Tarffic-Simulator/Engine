"""Pydantic response models for realtime session endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CreateRealtimeSessionResponse(BaseModel):
    """Response payload returned after creating a realtime session."""

    session_id: str = Field(description="Stable realtime session identifier.")
    run_id: str = Field(description="Execution run identifier.")
    status: str = Field(description="Initial run lifecycle status.")
    stream_url: Optional[str] = Field(default=None, description="Convenience URL for SSE reconnects.")
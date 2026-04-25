"""Simulation adapter that drives realtime runs through the existing SimulationManager."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from ...application.contracts import (
    CreateSimulationRequest,
    SimulationRuntimeGateway,
    StepSimulationRequest,
)
from ...domain.models import BoundingBox


class ManagerBackedSimulationModel:
    """Adapter that reuses the legacy SimulationManager for realtime execution."""

    def __init__(self, simulation_manager: SimulationRuntimeGateway) -> None:
        """Initialize the adapter.

        Args:
            simulation_manager: Existing synchronous simulation manager.
        """
        self.simulation_manager = simulation_manager
        self._simulation_id: Optional[str] = None

    def initialize_session(self, session_id: str, simulation_parameters: Dict[str, Any]) -> None:
        """Create the underlying simulation once for a realtime session."""
        if self._simulation_id is not None:
            return

        bbox_payload = simulation_parameters.get("bbox")
        bbox = BoundingBox(**bbox_payload) if bbox_payload else None
        request = CreateSimulationRequest(
            area=simulation_parameters.get("area"),
            bbox=bbox,
            config=dict(simulation_parameters.get("config") or {}),
        )
        response = self.simulation_manager.create_simulation(request)
        if not response.success:
            raise RuntimeError(response.error or f"Could not create realtime session {session_id}.")
        self._simulation_id = response.simulation_id

    def step(self) -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
        """Advance the underlying simulation by one tick."""
        if self._simulation_id is None:
            raise RuntimeError("Simulation must be initialized before stepping.")
        response = self.simulation_manager.step_simulation(
            self._simulation_id,
            StepSimulationRequest(n_ticks=1, actions=None),
        )
        if not response.success:
            raise RuntimeError(response.error or "Realtime step failed.")
        state = {"tick": response.new_tick}
        metrics = dict(response.metrics)
        metrics.setdefault("tick", response.new_tick)
        return state, metrics, False
"""Simulation adapter that drives realtime runs through the existing SimulationManager."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Dict, Optional, Tuple

from ...application.contracts import (
    CreateSimulationRequest,
    GetSnapshotRequest,
    SimulationRuntimeGateway,
    StepSimulationRequest,
)
from ...domain.models import BoundingBox


class ManagerBackedSimulationModel:
    """Adapter that reuses the legacy SimulationManager for realtime execution."""

    _current_session_id: ContextVar[Optional[str]] = ContextVar(
        "manager_backed_current_session_id",
        default=None,
    )

    def __init__(self, simulation_manager: SimulationRuntimeGateway) -> None:
        """Initialize the adapter.

        Args:
            simulation_manager: Existing synchronous simulation manager.
        """
        self.simulation_manager = simulation_manager
        self._simulation_ids_by_session: Dict[str, str] = {}

    def initialize_session(self, session_id: str, simulation_parameters: Dict[str, Any]) -> None:
        """Create the underlying simulation once for a realtime session.

        Args:
            session_id: Stable identifier for the realtime session.
            simulation_parameters: Parameters used to create the backing simulation.
        """
        simulation_id = self._simulation_ids_by_session.get(session_id)
        if simulation_id is not None:
            self._current_session_id.set(session_id)
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
        self._simulation_ids_by_session[session_id] = response.simulation_id
        self._current_session_id.set(session_id)

    def step(self) -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
        """Advance the underlying simulation by one tick."""
        simulation_id = self._resolve_current_simulation_id()
        if simulation_id is None:
            raise RuntimeError("Simulation must be initialized before stepping.")
        response = self.simulation_manager.step_simulation(
            simulation_id,
            StepSimulationRequest(n_ticks=1, actions=None),
        )
        if not response.success:
            raise RuntimeError(response.error or "Realtime step failed.")

        snapshot_response = self.simulation_manager.get_snapshot(
            simulation_id,
            GetSnapshotRequest(include_vehicle_details=True, include_edge_data=True),
        )
        snapshot = self._extract_snapshot(snapshot_response=snapshot_response)
        state = {"tick": response.new_tick, **snapshot}
        metrics = dict(response.metrics)
        metrics.setdefault("tick", response.new_tick)
        return state, metrics, False

    def _resolve_current_simulation_id(self) -> Optional[str]:
        """Return the simulation bound to the current execution context."""
        session_id = self._current_session_id.get()
        if session_id is None:
            return None
        return self._simulation_ids_by_session.get(session_id)

    def _extract_snapshot(self, snapshot_response: Any) -> Dict[str, Any]:
        """Normalize snapshot responses from manager implementations."""
        if isinstance(snapshot_response, dict):
            success = snapshot_response.get("success", True)
            if not success:
                raise RuntimeError(snapshot_response.get("error") or "Realtime snapshot retrieval failed.")
            snapshot = snapshot_response.get("snapshot")
        else:
            if not getattr(snapshot_response, "success", False):
                raise RuntimeError(
                    getattr(snapshot_response, "error", "") or "Realtime snapshot retrieval failed."
                )
            snapshot = getattr(snapshot_response, "snapshot", None)

        return dict(snapshot or {})
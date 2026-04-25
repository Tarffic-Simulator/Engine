"""Runtime contracts for background realtime execution."""

from __future__ import annotations

from typing import Any, Dict, Protocol

from .simulation_dto import CreateSimulationRequest, StepSimulationRequest


class RunExecutor(Protocol):
    """Abstraction for scheduling realtime session runs."""

    def submit(
        self,
        *,
        session_id: str,
        run_id: str,
        simulation_parameters: Dict[str, Any],
        runtime: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Submit a run for background execution."""


class SimulationRuntimeGateway(Protocol):
    """Boundary for synchronous simulation orchestration reused by realtime adapters."""

    def create_simulation(self, request: CreateSimulationRequest) -> Any:
        """Create one simulation instance and return a response object."""

    def step_simulation(
        self,
        simulation_id: str,
        request: StepSimulationRequest,
    ) -> Any:
        """Advance one simulation instance and return a response object."""


class SupportsShutdown(Protocol):
    """Optional lifecycle contract for runtime components."""

    async def shutdown(self) -> None:
        """Stop running background work and release resources."""
"""Use case for requesting a graceful simulation cancellation."""

from __future__ import annotations

from ...domain.exceptions import SimulationCancellationError, SimulationNotFoundError
from ...domain.models import SimulationRecord, SimulationStatus
from ..ports import SimulationRepository, SimulationRuntime


class CancelSimulationUseCase:
    def __init__(
        self,
        repository: SimulationRepository,
        runtime: SimulationRuntime,
    ) -> None:
        self.repository = repository
        self.runtime = runtime

    def execute(self, simulation_id: str) -> SimulationRecord:
        record = self.repository.get(simulation_id)
        if record is None:
            raise SimulationNotFoundError(f"Simulation '{simulation_id}' does not exist.")
        if record.status != SimulationStatus.RUNNING:
            raise SimulationCancellationError(
                f"Simulation '{simulation_id}' is already in status '{record.status.value}'."
            )
        if not self.runtime.cancel(simulation_id):
            raise SimulationCancellationError(
                f"Simulation '{simulation_id}' could not be cancelled because its runtime is not active."
            )
        return record

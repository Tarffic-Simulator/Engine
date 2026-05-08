"""Use case for retrieving simulation metadata."""

from __future__ import annotations

from ...domain.exceptions import SimulationNotFoundError
from ...domain.models import SimulationRecord
from ..ports import SimulationRepository


class GetSimulationUseCase:
    def __init__(self, repository: SimulationRepository) -> None:
        self.repository = repository

    def execute(self, simulation_id: str) -> SimulationRecord:
        record = self.repository.get(simulation_id)
        if record is None:
            raise SimulationNotFoundError(f"Simulation '{simulation_id}' does not exist.")
        return record

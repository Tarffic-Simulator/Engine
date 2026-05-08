"""Use case that executes a NaSch simulation in the background."""

from __future__ import annotations

import asyncio
from asyncio import Event
from typing import Any

from ...domain.models import GeographicArea, SimulationRecord, SimulationStatus, SimulationStep
from ...domain.simulation import NaSchSimulationModel
from ..ports import LiveEventBus, SimulationRepository


class RunSimulationUseCase:
    def __init__(
        self,
        repository: SimulationRepository,
        event_bus: LiveEventBus,
    ) -> None:
        self.repository = repository
        self.event_bus = event_bus

    async def execute(
        self,
        record: SimulationRecord,
        area: GeographicArea,
        cancel_event: Event,
    ) -> None:
        model = NaSchSimulationModel(seed=record.config.seed)
        model.reset(topology=area.topology, config=record.config)
        final_status = SimulationStatus.FINISHED

        try:
            for _ in range(record.config.max_steps):
                if cancel_event.is_set():
                    final_status = SimulationStatus.CANCELLED
                    break

                state, metrics, done = model.step()
                step = SimulationStep(
                    simulation_id=record.simulation_id,
                    step_number=state.step_number,
                    metrics=metrics,
                    state=state,
                )
                self.repository.append_step(step)
                self.repository.update_latest_step(record.simulation_id, latest_step=state.step_number)
                await self.event_bus.publish(
                    record.simulation_id,
                    {
                        "type": "step",
                        "simulation_id": record.simulation_id,
                        "status": SimulationStatus.RUNNING.value,
                        "step": step.to_dict(),
                    },
                )

                if done:
                    break

                if record.config.tick_interval_ms > 0:
                    try:
                        await asyncio.wait_for(
                            cancel_event.wait(),
                            timeout=record.config.tick_interval_ms / 1000,
                        )
                    except TimeoutError:
                        pass
                    if cancel_event.is_set():
                        final_status = SimulationStatus.CANCELLED
                        break
        finally:
            if cancel_event.is_set() and final_status == SimulationStatus.FINISHED:
                final_status = SimulationStatus.CANCELLED
            self.repository.update_status(record.simulation_id, status=final_status.value)
            await self.event_bus.publish(
                record.simulation_id,
                {
                    "type": "status",
                    "simulation_id": record.simulation_id,
                    "status": final_status.value,
                },
            )

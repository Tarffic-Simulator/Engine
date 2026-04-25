"""Use case for executing a realtime simulation run in the background."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Tuple

from ..contracts.realtime_entities import RealtimeTickRecord
from ..contracts.realtime_persistence import (
    SimulationRunRepository,
    SimulationSessionRepository,
    SimulationTickRepository,
)
from ..contracts.realtime_streaming import TickStreamBroker


class RunRealtimeSessionUseCase:
    """Execute a realtime run, persisting each tick before publication."""

    def __init__(
        self,
        session_repository: SimulationSessionRepository,
        run_repository: SimulationRunRepository,
        tick_repository: SimulationTickRepository,
        stream_broker: Optional[TickStreamBroker] = None,
        tick_stream_broker: Optional[TickStreamBroker] = None,
        simulation_model: Optional[Any] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        """Initialize the run orchestration dependencies."""
        self.session_repository = session_repository
        self.run_repository = run_repository
        self.tick_repository = tick_repository
        self.stream_broker = stream_broker or tick_stream_broker
        self.simulation_model = simulation_model
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    async def execute(
        self,
        session_id: str,
        run_id: str,
        max_ticks: Optional[int] = None,
        tick_limit: Optional[int] = None,
        tick_interval_ms: int = 0,
        worker_id: str = "in-process-worker",
    ) -> Dict[str, Any]:
        """Run the session until completion or until the configured limit is reached."""
        session = self.session_repository.get_session(session_id)
        if session is None:
            raise ValueError(f"Unknown realtime session '{session_id}'.")
        if self.simulation_model is None:
            raise RuntimeError("A simulation model is required to execute realtime runs.")

        self.session_repository.update_session_status(session_id, "running", self.clock())
        self.run_repository.mark_run_started(run_id, self.clock(), worker_id)

        resolved_max_ticks = self._resolve_max_ticks(session, max_ticks, tick_limit)
        await self._initialize_model_if_supported(session_id, session)

        last_tick_document: Optional[Dict[str, Any]] = None

        try:
            for iteration_index in range(resolved_max_ticks):
                state, metrics, done = await self._step_model()
                tick_number = self._resolve_tick_number(state, metrics, iteration_index)
                tick_record = RealtimeTickRecord(
                    session_id=session_id,
                    run_id=run_id,
                    tick_number=tick_number,
                    recorded_at=self.clock(),
                    metrics=self._normalize_mapping(metrics),
                    snapshot=self._normalize_optional_snapshot(state),
                    events=[],
                )
                tick_document = self.tick_repository.append_tick(tick_record.to_document())
                last_tick_document = tick_document
                self.session_repository.update_session_latest_tick(
                    session_id=session_id,
                    run_id=run_id,
                    tick_number=tick_document["tick_number"],
                    latest_metrics=dict(tick_document.get("metrics") or {}),
                    updated_at=self.clock(),
                )
                await self._publish_tick(run_id=run_id, tick_document=tick_document)

                if done:
                    break
                if tick_interval_ms > 0:
                    await asyncio.sleep(tick_interval_ms / 1000.0)

            completed_at = self.clock()
            self.run_repository.mark_run_completed(run_id, completed_at)
            self.session_repository.update_session_status(session_id, "completed", completed_at)
            await self._publish_terminal_event(
                run_id=run_id,
                session_id=session_id,
                status="completed",
                event_id=self._resolve_terminal_event_id(last_tick_document),
            )
            return {
                "session_id": session_id,
                "run_id": run_id,
                "status": "completed",
                "latest_tick": last_tick_document,
            }
        except Exception as exc:
            completed_at = self.clock()
            error = {"message": str(exc), "type": type(exc).__name__}
            self.run_repository.mark_run_failed(run_id, completed_at, error)
            self.session_repository.update_session_status(session_id, "failed", completed_at)
            await self._publish_terminal_event(
                run_id=run_id,
                session_id=session_id,
                status="failed",
                event_id=self._resolve_terminal_event_id(last_tick_document),
                error=error,
            )
            raise

    def _resolve_max_ticks(
        self,
        session: Dict[str, Any],
        max_ticks: Optional[int],
        tick_limit: Optional[int],
    ) -> int:
        """Resolve the maximum number of ticks to execute for one run."""
        configured_max_ticks = (
            max_ticks
            or tick_limit
            or int(session.get("simulation_parameters", {}).get("max_ticks", 100))
        )
        return max(1, configured_max_ticks)

    async def _initialize_model_if_supported(self, session_id: str, session: Dict[str, Any]) -> None:
        """Initialize the model lazily when an adapter supports it."""
        parameters = dict(session.get("simulation_parameters") or {})
        if hasattr(self.simulation_model, "initialize_session"):
            initializer = getattr(self.simulation_model, "initialize_session")
            result = initializer(session_id=session_id, simulation_parameters=parameters)
            if asyncio.iscoroutine(result):
                await result

    async def _step_model(self) -> Tuple[Any, Dict[str, Any], bool]:
        """Step the injected model, supporting sync and async adapters."""
        if hasattr(self.simulation_model, "step_async"):
            state, metrics, done = await self.simulation_model.step_async()
            return state, self._normalize_mapping(metrics), bool(done)

        state, metrics, done = self.simulation_model.step()
        return state, self._normalize_mapping(metrics), bool(done)

    def _resolve_tick_number(self, state: Any, metrics: Dict[str, Any], iteration_index: int) -> int:
        """Resolve a stable tick number from the step outputs."""
        if isinstance(metrics, dict) and isinstance(metrics.get("tick"), int):
            return metrics["tick"]
        if isinstance(state, dict) and isinstance(state.get("tick"), int):
            return state["tick"]
        return iteration_index + 1

    def _normalize_mapping(self, value: Any) -> Dict[str, Any]:
        """Convert step outputs into plain dictionaries."""
        if isinstance(value, dict):
            return dict(value)
        if hasattr(value, "__dict__"):
            return dict(value.__dict__)
        return {"value": value}

    def _normalize_optional_snapshot(self, state: Any) -> Optional[Dict[str, Any]]:
        """Convert a state payload into an optional snapshot document."""
        if state is None:
            return None
        if isinstance(state, dict):
            return dict(state)
        if hasattr(state, "__dict__"):
            return dict(state.__dict__)
        return {"value": state}

    def _resolve_terminal_event_id(self, tick_document: Optional[Dict[str, Any]]) -> int:
        """Return the numeric replay cursor to attach to a terminal SSE event."""
        if isinstance(tick_document, dict) and isinstance(tick_document.get("tick_number"), int):
            return tick_document["tick_number"]
        return -1

    async def _publish_tick(self, run_id: str, tick_document: Dict[str, Any]) -> None:
        """Publish a tick event if a broker is configured."""
        if self.stream_broker is None:
            return
        event = {
            "event": "tick",
            "id": str(tick_document["tick_number"]),
            "tick_number": tick_document["tick_number"],
            "data": dict(tick_document),
        }
        if hasattr(self.stream_broker, "publish_tick"):
            await self.stream_broker.publish_tick(run_id, event)
            return
        self.stream_broker.publish(run_id, event)

    async def _publish_terminal_event(
        self,
        run_id: str,
        session_id: str,
        status: str,
        event_id: int,
        error: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Publish one terminal run-status event when the broker supports it."""
        if self.stream_broker is None or not hasattr(self.stream_broker, "publish_terminal_event"):
            return
        await self.stream_broker.publish_terminal_event(
            run_id=run_id,
            event={
                "event": "run_status",
                "id": str(event_id),
                "data": {
                    "session_id": session_id,
                    "run_id": run_id,
                    "status": status,
                    "error": dict(error or {}) or None,
                },
            },
        )

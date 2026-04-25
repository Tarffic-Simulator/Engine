"""In-process asyncio-backed run executor for local realtime sessions."""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from ...application.use_cases.run_realtime_session import RunRealtimeSessionUseCase


class InProcessRunExecutor:
    """Schedule realtime session runs on the active asyncio event loop."""

    def __init__(self, run_use_case: RunRealtimeSessionUseCase, worker_id: str = "in-process-worker") -> None:
        """Initialize the executor.

        Args:
            run_use_case: Use case executed in background tasks.
            worker_id: Stable worker identifier stored in run runtime metadata.
        """
        self.run_use_case = run_use_case
        self.worker_id = worker_id
        self._tasks: Dict[str, asyncio.Task] = {}

    def submit(
        self,
        *,
        session_id: str,
        run_id: str,
        simulation_parameters: Dict[str, Any],
        runtime: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Schedule one realtime run on the current event loop."""
        loop = asyncio.get_running_loop()
        task = loop.create_task(
            self.run_use_case.execute(
                session_id=session_id,
                run_id=run_id,
                max_ticks=int(runtime.get("max_ticks", simulation_parameters.get("max_ticks", 100))),
                tick_interval_ms=int(runtime.get("tick_interval_ms", 250)),
                worker_id=self.worker_id,
            )
        )
        self._tasks[run_id] = task
        task.add_done_callback(lambda finished_task, run_key=run_id: self._cleanup_task(run_key, finished_task))
        return {"accepted": True, "run_id": run_id}

    async def shutdown(self) -> None:
        """Cancel all outstanding background tasks."""
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

    def _cleanup_task(self, run_id: str, task: asyncio.Task) -> None:
        """Remove finished tasks from the registry and consume exceptions."""
        self._tasks.pop(run_id, None)
        try:
            task.result()
        except asyncio.CancelledError:
            return
        except Exception:
            return
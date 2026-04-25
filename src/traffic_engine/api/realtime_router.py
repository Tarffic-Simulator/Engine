"""FastAPI routes for realtime session creation and SSE replay."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from .models.realtime_requests import CreateRealtimeSessionRequest
from .models.realtime_responses import CreateRealtimeSessionResponse
from .simulation_manager import SimulationManager
from ..application.use_cases.replay_and_stream_ticks import ReplayAndStreamTicksUseCase
from ..application.use_cases.run_realtime_session import RunRealtimeSessionUseCase
from ..application.use_cases.start_realtime_session import StartRealtimeSessionUseCase
from ..infrastructure.persistence.mongo_realtime_repositories import (
    MongoSimulationRunRepository,
    MongoSimulationSessionRepository,
    MongoSimulationTickRepository,
)
from ..infrastructure.realtime.in_memory_tick_stream import InMemoryTickStreamBroker
from ..infrastructure.runtime.in_process_run_executor import InProcessRunExecutor
from ..infrastructure.runtime.manager_backed_simulation_model import ManagerBackedSimulationModel


router = APIRouter(prefix="/realtime", tags=["realtime"])


class RealtimeServiceContainer:
    """Container for lazily composed realtime service dependencies."""

    def __init__(self) -> None:
        """Create the realtime service graph."""
        session_repository = MongoSimulationSessionRepository()
        run_repository = MongoSimulationRunRepository()
        tick_repository = MongoSimulationTickRepository()
        stream_broker = InMemoryTickStreamBroker()
        simulation_model = ManagerBackedSimulationModel(SimulationManager())
        run_use_case = RunRealtimeSessionUseCase(
            session_repository=session_repository,
            run_repository=run_repository,
            tick_repository=tick_repository,
            stream_broker=stream_broker,
            simulation_model=simulation_model,
        )
        run_executor = InProcessRunExecutor(run_use_case=run_use_case)

        self.session_repository = session_repository
        self.run_repository = run_repository
        self.tick_repository = tick_repository
        self.stream_broker = stream_broker
        self.run_executor = run_executor
        self.start_use_case = StartRealtimeSessionUseCase(
            session_repository=session_repository,
            run_repository=run_repository,
            tick_repository=tick_repository,
            run_executor=run_executor,
        )
        self.replay_use_case = ReplayAndStreamTicksUseCase(
            tick_repository=tick_repository,
            stream_broker=stream_broker,
        )


@lru_cache(maxsize=1)
def get_realtime_services() -> RealtimeServiceContainer:
    """Return cached realtime services backed by environment-driven Mongo settings."""
    return RealtimeServiceContainer()


def _resolve_services() -> RealtimeServiceContainer:
    """Resolve realtime services and map configuration failures to HTTP errors."""
    try:
        return get_realtime_services()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post(
    "/sessions",
    response_model=CreateRealtimeSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_realtime_session(
    request: CreateRealtimeSessionRequest,
    http_request: Request,
    services: RealtimeServiceContainer = Depends(_resolve_services),
) -> CreateRealtimeSessionResponse:
    """Create a realtime session and dispatch background execution."""
    runtime = request.runtime.dict()
    result = services.start_use_case.execute(
        session_id=request.session_id,
        run_id=request.run_id,
        simulation_parameters=request.to_simulation_parameters(),
        runtime=runtime,
    )
    stream_url = str(
        http_request.url_for(
            "stream_realtime_session",
            session_id=result["session_id"],
        )
    )
    return CreateRealtimeSessionResponse(
        session_id=result["session_id"],
        run_id=result["run_id"],
        status=result["status"],
        stream_url=f"{stream_url}?run_id={result['run_id']}",
    )


@router.get(
    "/sessions/{session_id}/stream",
    name="stream_realtime_session",
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": "Realtime replay and live stream.",
        }
    },
)
async def stream_realtime_session(
    session_id: str,
    run_id: str = Query(..., description="Execution identifier to replay and follow."),
    from_tick: int = Query(-1, description="Replay ticks strictly after this tick number."),
    follow: bool = Query(True, description="Continue with live events after replay."),
    last_event_id: Optional[str] = Header(default=None, alias="Last-Event-ID"),
    services: RealtimeServiceContainer = Depends(_resolve_services),
) -> StreamingResponse:
    """Replay persisted ticks and optionally continue with live SSE events."""
    stream = await services.replay_use_case.execute(
        session_id=session_id,
        run_id=run_id,
        from_tick=from_tick,
        follow=follow,
        last_event_id=last_event_id,
    )
    return StreamingResponse(stream, media_type="text/event-stream")
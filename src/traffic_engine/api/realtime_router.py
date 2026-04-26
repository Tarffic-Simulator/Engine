"""FastAPI routes for realtime session creation, history browsing, and live replay."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse

from .models.realtime_requests import CreateRealtimeSessionRequest, ExtendRealtimeRunRequest
from .models.realtime_responses import (
    CreateRealtimeSessionResponse,
    ListRealtimeRunsResponse,
    ListRealtimeSessionsResponse,
    ListRealtimeTicksResponse,
    RealtimeAvailabilityResponse,
)
from .simulation_manager import SimulationManager
from ..application.use_cases.list_realtime_runs import ListRealtimeRunsUseCase
from ..application.use_cases.list_realtime_sessions import ListRealtimeSessionsUseCase
from ..application.use_cases.list_realtime_ticks import ListRealtimeTicksUseCase
from ..application.use_cases.extend_realtime_session import ExtendRealtimeSessionUseCase
from ..application.use_cases.replay_and_stream_ticks import ReplayAndStreamTicksUseCase
from ..application.use_cases.run_realtime_session import RunRealtimeSessionUseCase
from ..application.use_cases.start_realtime_session import StartRealtimeSessionUseCase
from ..application.use_cases.stream_realtime_events import StreamRealtimeEventsUseCase
from ..infrastructure.persistence.mongo_realtime_repositories import (
    MongoSimulationRunRepository,
    MongoSimulationSessionRepository,
    MongoSimulationTickRepository,
)
from ..infrastructure.realtime.in_memory_tick_stream import InMemoryTickStreamBroker
from ..infrastructure.runtime.in_process_run_executor import InProcessRunExecutor
from ..infrastructure.runtime.manager_backed_simulation_model import ManagerBackedSimulationModel


router = APIRouter(prefix="/realtime", tags=["realtime"])

REALTIME_UNAVAILABLE_MESSAGE = (
    "Realtime persistence is not configured. Start MongoDB and configure the API "
    "persistence connection before using realtime history."
)


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
        self.extend_use_case = ExtendRealtimeSessionUseCase(
            session_repository=session_repository,
            run_repository=run_repository,
            tick_repository=tick_repository,
            run_executor=run_executor,
        )
        self.list_sessions_use_case = ListRealtimeSessionsUseCase(
            session_repository=session_repository,
        )
        self.list_runs_use_case = ListRealtimeRunsUseCase(
            run_repository=run_repository,
        )
        self.list_ticks_use_case = ListRealtimeTicksUseCase(
            tick_repository=tick_repository,
        )
        self.replay_use_case = ReplayAndStreamTicksUseCase(
            tick_repository=tick_repository,
            stream_broker=stream_broker,
        )
        self.stream_events_use_case = StreamRealtimeEventsUseCase(
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
            detail=REALTIME_UNAVAILABLE_MESSAGE,
        ) from exc


def _build_websocket_url(request: Request, session_id: str, run_id: str) -> str:
    """Return the canonical public WebSocket URL for a realtime run."""
    base_url = str(request.base_url).rstrip("/")
    websocket_base = base_url.replace("http://", "ws://", 1).replace("https://", "wss://", 1)
    query_string = urlencode([("run_id", run_id)])
    return f"{websocket_base}/realtime/sessions/{session_id}/ws?{query_string}"


def _build_stream_url(request: Request, session_id: str, run_id: str) -> str:
    """Return the compatibility SSE URL for a realtime run."""
    stream_url = str(
        request.url_for(
            "stream_realtime_session",
            session_id=session_id,
        )
    )
    return f"{stream_url}?{urlencode([('run_id', run_id)])}"


def _create_session_response(
    *,
    request: Request,
    result: Dict[str, Any],
) -> CreateRealtimeSessionResponse:
    """Construct the public create/extend response payload."""
    run_status = result.get("run_status", result.get("status"))
    session_status = result.get("session_status", run_status)
    session_id = str(result["session_id"])
    run_id = str(result["run_id"])
    return CreateRealtimeSessionResponse(
        session_id=session_id,
        run_id=run_id,
        session_status=session_status,
        run_status=run_status,
        status=run_status,
        websocket_url=_build_websocket_url(request=request, session_id=session_id, run_id=run_id),
        stream_url=_build_stream_url(request=request, session_id=session_id, run_id=run_id),
    )


def _resolve_default_run_id(
    *,
    session_id: str,
    services: RealtimeServiceContainer,
) -> Optional[str]:
    """Resolve the default run identifier for a session when one is not supplied."""
    session = services.session_repository.get_session(session_id)
    if session is None:
        return None
    latest_run_id = session.get("latest_run_id")
    return str(latest_run_id) if latest_run_id else None


def _run_belongs_to_session(
    *,
    session_id: str,
    run_id: str,
    services: RealtimeServiceContainer,
) -> bool:
    """Return whether a run exists and belongs to the requested session."""
    run_document = services.run_repository.get_run(run_id)
    if run_document is None:
        return False
    return str(run_document.get("session_id") or "") == session_id


@router.get(
    "/status",
    response_model=RealtimeAvailabilityResponse,
)
async def realtime_status() -> RealtimeAvailabilityResponse:
    """Expose client-safe realtime persistence availability."""
    try:
        get_realtime_services()
    except RuntimeError:
        return RealtimeAvailabilityResponse(
            available=False,
            status="unavailable",
            message=REALTIME_UNAVAILABLE_MESSAGE,
        )

    return RealtimeAvailabilityResponse(
        available=True,
        status="available",
        message="Realtime persistence is available.",
    )


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
    return _create_session_response(request=http_request, result=result)


@router.post(
    "/sessions/{session_id}/runs",
    response_model=CreateRealtimeSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def extend_realtime_session(
    session_id: str,
    request: ExtendRealtimeRunRequest,
    http_request: Request,
    services: RealtimeServiceContainer = Depends(_resolve_services),
) -> CreateRealtimeSessionResponse:
    """Create and dispatch a new run for an existing finished realtime session."""
    result = services.extend_use_case.execute(
        session_id=session_id,
        n_steps=request.n_steps,
        runtime=request.to_runtime(),
        run_id=request.run_id,
    )
    return _create_session_response(request=http_request, result=result)


@router.get(
    "/sessions",
    response_model=ListRealtimeSessionsResponse,
)
async def list_realtime_sessions(
    status: Optional[str] = Query(default=None, description="Optional lifecycle status filter."),
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of sessions to return."),
    services: RealtimeServiceContainer = Depends(_resolve_services),
) -> ListRealtimeSessionsResponse:
    """List persisted realtime sessions for external client replay selection."""
    return ListRealtimeSessionsResponse(**services.list_sessions_use_case.execute(status=status, limit=limit))


@router.get(
    "/sessions/{session_id}/runs",
    response_model=ListRealtimeRunsResponse,
)
async def list_realtime_runs(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of runs to return."),
    services: RealtimeServiceContainer = Depends(_resolve_services),
) -> ListRealtimeRunsResponse:
    """List persisted runs for one realtime session."""
    return ListRealtimeRunsResponse(**services.list_runs_use_case.execute(session_id=session_id, limit=limit))


@router.get(
    "/sessions/{session_id}/ticks",
    response_model=ListRealtimeTicksResponse,
)
async def list_realtime_ticks(
    session_id: str,
    run_id: str = Query(..., description="Execution identifier to browse."),
    from_tick: int = Query(-1, description="Return ticks strictly after this tick number."),
    limit: int = Query(default=200, ge=1, le=1000, description="Maximum number of ticks to return."),
    services: RealtimeServiceContainer = Depends(_resolve_services),
) -> ListRealtimeTicksResponse:
    """List persisted ticks for one realtime session run."""
    return ListRealtimeTicksResponse(
        **services.list_ticks_use_case.execute(
            session_id=session_id,
            run_id=run_id,
            from_tick=from_tick,
            limit=limit,
        )
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


@router.websocket(
    "/sessions/{session_id}/ws",
    name="realtime_session_websocket",
)
async def stream_realtime_session_websocket(
    websocket: WebSocket,
    session_id: str,
    run_id: Optional[str] = None,
    from_tick: int = -1,
    follow: bool = True,
    services: RealtimeServiceContainer = Depends(_resolve_services),
) -> None:
    """Replay persisted events and optionally continue with the live WebSocket stream."""
    resolved_run_id = run_id or _resolve_default_run_id(session_id=session_id, services=services)
    await websocket.accept()

    if resolved_run_id is None:
        await websocket.send_json(
            {
                "event": "error",
                "session_id": session_id,
                "run_id": "",
                "cursor": from_tick,
                "sent_at": "",
                "data": {"message": f"No run found for realtime session '{session_id}'."},
            }
        )
        await websocket.close(code=4404)
        return

    if not _run_belongs_to_session(
        session_id=session_id,
        run_id=resolved_run_id,
        services=services,
    ):
        await websocket.send_json(
            {
                "event": "error",
                "session_id": session_id,
                "run_id": resolved_run_id,
                "cursor": from_tick,
                "sent_at": "",
                "data": {
                    "message": (
                        f"Run '{resolved_run_id}' does not belong to realtime session '{session_id}'."
                    )
                },
            }
        )
        await websocket.close(code=4404)
        return

    try:
        stream = await services.stream_events_use_case.execute(
            session_id=session_id,
            run_id=resolved_run_id,
            from_tick=from_tick,
            follow=follow,
        )
        async for event in stream:
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            return
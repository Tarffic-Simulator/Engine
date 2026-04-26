"""FastAPI application for Traffic Engine."""

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    CreateRealtimeSessionResponse,
    CreateSimulationRequest,
    CreateSimulationResponse,
    GetMetricsRequest as ApiGetMetricsRequest,
    GetMetricsResponse,
    GetSnapshotRequest as ApiGetSnapshotRequest,
    GetSnapshotResponse,
    StepSimulationRequest,
    StepSimulationResponse,
)
from .realtime_router import get_realtime_services, router as realtime_router
from .simulation_manager import SimulationManager
from ..application.contracts import (
    CreateSimulationRequest as CreateSimulationDto,
    GetMetricsRequest as GetMetricsDto,
    GetSnapshotRequest as GetSnapshotDto,
    StepSimulationRequest as StepSimulationDto,
)
from ..domain.models import BoundingBox, VehicleType
from ..infrastructure.persistence import close_mongo_client

# Initialize FastAPI app
app = FastAPI(
    title="Traffic Engine API",
    description="REST API for traffic simulation engine with cellular automata",
    version="1.0.0"
)

# CORS middleware for external API consumers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize simulation manager
simulation_manager = SimulationManager()
app.include_router(realtime_router)


def _to_create_simulation_dto(request: CreateSimulationRequest) -> CreateSimulationDto:
    """Convert API request data into the application DTO."""
    bbox = BoundingBox(**request.bbox) if request.bbox else None
    return CreateSimulationDto(
        area=request.area,
        bbox=bbox,
        config=dict(request.config or {}),
    )


def _to_step_simulation_dto(request: StepSimulationRequest) -> StepSimulationDto:
    """Convert API request data into the application DTO."""
    return StepSimulationDto(
        n_ticks=request.n_ticks,
        actions=dict(request.actions or {}) or None,
    )


def _to_metrics_dto(request: ApiGetMetricsRequest) -> GetMetricsDto:
    """Convert API request data into the application DTO."""
    return GetMetricsDto(
        include_history=request.include_history,
        window_ticks=request.window_ticks,
    )


def _to_snapshot_dto(request: ApiGetSnapshotRequest) -> GetSnapshotDto:
    """Convert API request data into the application DTO."""
    try:
        vehicle_types = [VehicleType(value) for value in request.vehicle_types_filter or []]
    except ValueError as exc:
        valid_values = ", ".join(vehicle_type.value for vehicle_type in VehicleType)
        raise HTTPException(
            status_code=422,
            detail=(
                "vehicle_types_filter contains an invalid value. "
                f"Expected one of: {valid_values}."
            ),
        ) from exc

    return GetSnapshotDto(
        include_vehicle_details=request.include_vehicle_details,
        include_edge_data=request.include_edge_data,
        vehicle_types_filter=vehicle_types or None,
    )


def _to_create_simulation_response(response: object) -> CreateSimulationResponse:
    """Convert internal response data into the public API response model."""
    return CreateSimulationResponse(
        success=response.success,
        error=response.error or None,
        simulation_id=response.simulation_id,
        initial_state=response.initial_state,
        topology_summary=response.topology_summary,
        traffic_lights_count=response.traffic_lights_count,
    )


def _to_step_simulation_response(response: object) -> StepSimulationResponse:
    """Convert internal response data into the public API response model."""
    return StepSimulationResponse(
        success=response.success,
        error=response.error or None,
        simulation_id=response.simulation_id,
        new_tick=response.new_tick,
        metrics=response.metrics,
        vehicles_spawned=response.vehicles_spawned,
        vehicles_removed=response.vehicles_removed,
    )


def _to_metrics_response(response: object) -> GetMetricsResponse:
    """Convert internal response data into the public API response model."""
    return GetMetricsResponse(
        success=response.success,
        error=response.error or None,
        simulation_id=response.simulation_id,
        current_metrics=response.current_metrics,
        history=response.history,
    )


def _to_snapshot_response(response: object) -> GetSnapshotResponse:
    """Convert internal response data into the public API response model."""
    return GetSnapshotResponse(
        success=response.success,
        error=response.error or None,
        simulation_id=response.simulation_id,
        snapshot=response.snapshot,
    )


@app.post("/simulations", response_model=CreateSimulationResponse)
async def create_simulation(request: CreateSimulationRequest) -> CreateSimulationResponse:
    """Create a new traffic simulation instance."""
    response = simulation_manager.create_simulation(_to_create_simulation_dto(request))
    return _to_create_simulation_response(response)


@app.post("/simulations/{simulation_id}/step", response_model=StepSimulationResponse)
async def step_simulation(
    simulation_id: str, 
    request: StepSimulationRequest
) -> StepSimulationResponse:
    """Advance simulation by specified number of ticks."""
    response = simulation_manager.step_simulation(simulation_id, _to_step_simulation_dto(request))
    return _to_step_simulation_response(response)


@app.get("/simulations/{simulation_id}/metrics", response_model=GetMetricsResponse)
async def get_metrics(
    simulation_id: str,
    include_history: bool = False,
    window_ticks: Optional[int] = None
) -> GetMetricsResponse:
    """Get current metrics for a simulation."""
    request = ApiGetMetricsRequest(
        include_history=include_history,
        window_ticks=window_ticks or 60
    )
    response = simulation_manager.get_metrics(simulation_id, _to_metrics_dto(request))
    return _to_metrics_response(response)


@app.get("/simulations/{simulation_id}/snapshot", response_model=GetSnapshotResponse)
async def get_snapshot(
    simulation_id: str,
    include_vehicle_details: bool = False,
    include_edge_data: bool = False,
    vehicle_types_filter: Optional[List[str]] = None
) -> GetSnapshotResponse:
    """Get detailed snapshot of simulation state."""
    request = ApiGetSnapshotRequest(
        include_vehicle_details=include_vehicle_details,
        include_edge_data=include_edge_data,
        vehicle_types_filter=vehicle_types_filter or []
    )
    response = simulation_manager.get_snapshot(simulation_id, _to_snapshot_dto(request))
    return _to_snapshot_response(response)


@app.delete("/simulations/{simulation_id}")
async def delete_simulation(simulation_id: str) -> dict:
    """Delete a simulation instance."""
    success = simulation_manager.delete_simulation(simulation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {"message": f"Simulation {simulation_id} deleted successfully"}


@app.get("/simulations")
async def list_simulations() -> dict:
    """List all active simulation instances."""
    instances = simulation_manager.list_simulations()
    return {
        "simulations": instances,
        "count": len(instances)
    }


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "message": "Traffic Engine API is running"}


@app.on_event("shutdown")
async def shutdown_realtime_services() -> None:
    """Shut down background realtime services when the app stops."""
    if get_realtime_services.cache_info().currsize > 0:
        services = get_realtime_services()
        if hasattr(services.run_executor, "shutdown"):
            await services.run_executor.shutdown()

    close_mongo_client()


def main() -> None:
    """Run the API with uvicorn for the console entry point."""
    import uvicorn

    uvicorn.run("traffic_engine.api.app:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
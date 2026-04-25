"""
Data Transfer Objects (DTOs) for simulation use cases.

Defines the request/response structures for application layer operations,
providing clean interfaces between API and domain layers.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from ...domain.models import BoundingBox, VehicleType


@dataclass
class CreateSimulationRequest:
    """
    Request data for creating a new simulation.
    
    Attributes:
        area: Named geographic area (e.g., "Polanco, CDMX") - mutually exclusive with bbox
        bbox: Geographic bounding box - mutually exclusive with area
        config: Optional simulation configuration overrides
    """
    area: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    config: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate that exactly one of area or bbox is provided."""
        if not ((self.area is None) ^ (self.bbox is None)):
            raise ValueError("Must provide exactly one of 'area' or 'bbox'")


@dataclass
class CreateSimulationResponse:
    """
    Response data after creating a simulation.
    
    Attributes:
        simulation_id: Unique identifier for the new simulation
        initial_state: Initial simulation state after setup
        topology_summary: Brief summary of loaded topology
        traffic_lights_count: Number of traffic lights configured
        success: True if creation successful
        error: Error message if success is False
    """
    simulation_id: str
    initial_state: Dict[str, Any]
    topology_summary: Dict[str, Any]
    traffic_lights_count: int
    success: bool = True
    error: str = ""


@dataclass
class StepSimulationRequest:
    """
    Request data for advancing simulation.
    
    Attributes:
        n_ticks: Number of simulation ticks to advance
        actions: Optional actions to apply during step
    """
    n_ticks: int = 1
    actions: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate request parameters."""
        if self.n_ticks < 1:
            raise ValueError("n_ticks must be positive")
        if self.n_ticks > 100:  # Reasonable upper limit
            raise ValueError("n_ticks cannot exceed 100")


@dataclass
class StepSimulationResponse:
    """
    Response data after stepping simulation.
    
    Attributes:
        simulation_id: Simulation identifier
        new_tick: Simulation tick after step
        metrics: Aggregated performance metrics
        vehicles_spawned: Number of new vehicles added
        vehicles_removed: Number of vehicles that exited
        success: True if step successful
        error: Error message if success is False
    """
    simulation_id: str
    new_tick: int
    metrics: Dict[str, Any]
    vehicles_spawned: int
    vehicles_removed: int
    success: bool = True
    error: str = ""


@dataclass
class GetMetricsRequest:
    """
    Request data for retrieving simulation metrics.
    
    Attributes:
        include_history: Whether to include historical metric trends
        window_ticks: Number of recent ticks to include in history
    """
    include_history: bool = False
    window_ticks: int = 60


@dataclass
class GetMetricsResponse:
    """
    Response data with simulation metrics.
    
    Attributes:
        simulation_id: Simulation identifier
        current_metrics: Current tick metrics
        history: Optional historical metrics if requested
        success: True if retrieval successful
        error: Error message if success is False
    """
    simulation_id: str
    current_metrics: Dict[str, Any]
    history: Optional[List[Dict[str, Any]]] = None
    success: bool = True
    error: str = ""


@dataclass
class GetSnapshotRequest:
    """
    Request data for retrieving detailed simulation snapshot.
    
    Attributes:
        include_vehicle_details: Whether to include detailed vehicle info
        include_edge_data: Whether to include edge-level data
        vehicle_types_filter: Optional filter for specific vehicle types
    """
    include_vehicle_details: bool = True
    include_edge_data: bool = True
    vehicle_types_filter: Optional[List[VehicleType]] = None


@dataclass
class GetSnapshotResponse:
    """
    Response data with detailed simulation snapshot.
    
    Attributes:
        simulation_id: Simulation identifier
        snapshot: Complete simulation snapshot data
        success: True if retrieval successful
        error: Error message if success is False
    """
    simulation_id: str
    snapshot: Dict[str, Any]
    success: bool = True
    error: str = ""


@dataclass
class SimulationConfigDto:
    """
    Configuration parameters for simulation initialization.
    
    Attributes:
        initial_vehicles: Number of vehicles to spawn initially
        max_vehicles: Maximum concurrent vehicles
        spawn_rate: Vehicle spawn rate per boundary node per tick
        noise_prob: Base NaSch noise probability
        timeout_ticks: Ticks before stationary vehicles are removed
        cell_size_m: Cell size in meters (affects discretization)
        max_ticks: Maximum simulation duration
        traffic_light_config: Traffic light configuration overrides
    """
    initial_vehicles: int = 0
    max_vehicles: int = 1000
    spawn_rate: float = 0.1
    noise_prob: float = 0.28
    timeout_ticks: int = 50
    cell_size_m: float = 5.0
    max_ticks: int = 10000
    traffic_light_config: Optional[Dict[str, Any]] = None
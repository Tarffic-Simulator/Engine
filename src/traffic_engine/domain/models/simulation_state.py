"""
Simulation state and metrics models.

Defines the complete simulation state and aggregated metrics structures
for tracking simulation progress and providing API responses.
"""

from dataclasses import dataclass
from typing import Dict, List
from .vehicles import VehicleState
from .traffic_lights import LightState
from .topology import EdgeId


@dataclass
class SimulationState:
    """
    Complete simulation state snapshot.
    
    Contains all information about the current state of the simulation,
    including vehicles, traffic lights, and temporal information.
    
    Attributes:
        tick: Current simulation time step
        vehicles: List of all active vehicle states
        traffic_lights: List of all traffic light states  
        total_vehicles: Total number of active vehicles
        active_vehicles: Number of vehicles currently moving
    """
    tick: int
    vehicles: List[VehicleState]
    traffic_lights: List[LightState]
    total_vehicles: int
    active_vehicles: int


@dataclass 
class Metrics:
    """
    Aggregated simulation metrics for analysis and optimization.
    
    Provides key performance indicators derived from the current simulation state,
    optimized for API consumers focused on traffic analysis.
    
    Attributes:
        tick: Current simulation time step
        total_vehicles: Total number of active vehicles
        avg_speed_kmh: Average vehicle speed in km/h
        density: Fraction of road cells occupied by vehicles [0.0, 1.0]
        throughput_veh_per_min: Vehicles exiting network per minute
        congestion_ratio: Fraction of vehicles with zero velocity [0.0, 1.0]
        boundary_inflow: Vehicles entering from boundary per minute
        boundary_outflow: Vehicles exiting to boundary per minute
    """
    tick: int
    total_vehicles: int
    avg_speed_kmh: float
    density: float
    throughput_veh_per_min: float
    congestion_ratio: float
    boundary_inflow: float
    boundary_outflow: float


@dataclass
class SnapshotData:
    """
    Detailed simulation snapshot optimized for visualization.
    
    Contains comprehensive state information needed for rendering
    the simulation in dashboards and analysis tools.
    
    Attributes:
        tick: Current simulation time step
        vehicles: Detailed vehicle state list with positions
        traffic_lights: Traffic light states with timing info
        edge_densities: Density (occupied fraction) by edge
        edge_flows: Current vehicle count by edge
        bbox: Geographic bounding box of simulation area
    """
    tick: int
    vehicles: List[VehicleState]
    traffic_lights: List[LightState]
    edge_densities: Dict[EdgeId, float]
    edge_flows: Dict[EdgeId, int]
    bbox: Dict[str, float]  # {'min_x', 'max_x', 'min_y', 'max_y'}


@dataclass
class StepResult:
    """
    Result of a simulation step operation.
    
    Contains the updated state and metrics after advancing the simulation,
    plus information about what happened during the step.
    
    Attributes:
        success: True if step completed successfully
        new_state: Updated simulation state after step
        metrics: Computed metrics for this step
        vehicles_spawned: Number of new vehicles added
        vehicles_removed: Number of vehicles that exited/despawned
        error: Error message if success is False
    """
    success: bool
    new_state: SimulationState
    metrics: Metrics
    vehicles_spawned: int
    vehicles_removed: int
    error: str = ""
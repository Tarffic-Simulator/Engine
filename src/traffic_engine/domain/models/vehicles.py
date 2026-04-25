"""
Vehicle domain models for traffic simulation.

Defines vehicle types, states, and behaviors based on the prototype implementation
with support for heterogeneous driver behavior and realistic vehicle dynamics.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional
from .topology import EdgeId


class VehicleType(Enum):
    """Vehicle type enumeration matching prototype implementation."""
    CAR = "car"
    BUS = "bus" 
    MOTO = "moto"


@dataclass
class VehicleTypeConfig:
    """
    Configuration parameters for each vehicle type.
    
    Based on VTYPE_CONFIG from prototype with realistic urban parameters.
    
    Attributes:
        speed_factor: Multiplier for base speed (1.0=normal, 0.55=slow bus, 1.25=fast moto)
        noise_factor: Multiplier for random braking probability
        size_cells: Vehicle size in cells (affects visualization and spacing)
        color: Color for visualization (None = dynamic based on speed)
    """
    speed_factor: float
    noise_factor: float
    size_cells: int
    color: Optional[str] = None


# Vehicle type configurations from prototype
VEHICLE_TYPE_CONFIGS = {
    VehicleType.CAR: VehicleTypeConfig(
        speed_factor=1.0, 
        noise_factor=1.0, 
        size_cells=1, 
        color=None  # Dynamic color based on speed
    ),
    VehicleType.BUS: VehicleTypeConfig(
        speed_factor=0.55, 
        noise_factor=0.6, 
        size_cells=2, 
        color='#f39c12'  # Orange
    ),
    VehicleType.MOTO: VehicleTypeConfig(
        speed_factor=1.25, 
        noise_factor=1.5, 
        size_cells=1, 
        color='#9b59b6'  # Purple
    ),
}


@dataclass
class Vehicle:
    """
    Represents a vehicle in the simulation with complete state tracking.
    
    Based on Vehicle dataclass from prototype with individual driver heterogeneity
    and realistic movement tracking through the road network.
    
    Attributes:
        vid: Unique vehicle identifier
        vtype: Vehicle type (car/bus/moto)
        route: List of edges forming the vehicle's path
        noise_prob: Individual probability of random braking [0,1]
        vmax_factor: Individual speed factor [0.7, 1.3] 
        edge_idx: Current index in route (which edge vehicle is on)
        cell_pos: Position within current edge (0 to n_cells-1)
        velocity: Current velocity in cells per tick
        distance_traveled_m: Total distance traveled since spawn
        wait_ticks: Number of consecutive ticks with zero velocity
    """
    vid: int
    vtype: VehicleType
    route: List[EdgeId]
    noise_prob: float
    vmax_factor: float
    edge_idx: int = 0
    cell_pos: int = 0
    velocity: int = 0
    distance_traveled_m: float = 0.0
    wait_ticks: int = 0
    
    @property
    def current_edge(self) -> EdgeId:
        """Get the edge the vehicle is currently on."""
        return self.route[self.edge_idx]
    
    @property 
    def next_edge(self) -> Optional[EdgeId]:
        """Get the next edge in the vehicle's route, or None if at destination."""
        next_idx = self.edge_idx + 1
        return self.route[next_idx] if next_idx < len(self.route) else None
    
    def get_config(self) -> VehicleTypeConfig:
        """Get the configuration for this vehicle's type."""
        return VEHICLE_TYPE_CONFIGS[self.vtype]


@dataclass
class VehicleState:
    """
    Snapshot of vehicle state for API responses and visualization.
    
    Contains the essential information needed for rendering and analysis
    without internal simulation details.
    
    Attributes:
        vid: Vehicle identifier
        vtype: Vehicle type
        x: Geographic longitude  
        y: Geographic latitude
        edge: Current edge ID
        velocity: Current velocity in cells/tick
        speed_kmh: Current speed in km/h
        wait_ticks: Ticks spent stationary
    """
    vid: int
    vtype: VehicleType
    x: float
    y: float
    edge: EdgeId
    velocity: int
    speed_kmh: float
    wait_ticks: int
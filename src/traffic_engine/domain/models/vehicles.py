"""
Vehicle domain models for traffic simulation.

Defines vehicle types, states, and behaviors based on the prototype implementation
with support for heterogeneous driver behavior and realistic vehicle dynamics.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

import numpy as np

from .topology import EdgeId, NodeId


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
        color='#f39c12'
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
        lane_index: Current lane position within edge (zero-based)
        lateral_offset_m: Lateral visualization offset in meters from lane centerline
        impatience_ticks: Consecutive ticks while constrained below desired speed
        lane_change_cooldown: Ticks remaining before another lane change can occur
        render_label: Optional stable label for visualization
        render_color: Optional stable color override for visualization
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
    lane_index: int = 0
    lateral_offset_m: float = 0.0
    impatience_ticks: int = 0
    lane_change_cooldown: int = 0
    render_label: Optional[str] = None
    render_color: Optional[str] = None
    
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
class PublicTransport(Vehicle):
    """Transit vehicle specialization with station dwell behavior.

    Attributes:
        station_node_ids: Ordered station nodes where this bus can dwell.
        current_station_idx: Current target station index.
        is_dwelling: Whether the bus is currently stopped at a station.
        dwell_ticks_remaining: Remaining ticks to stay at the stop.
    """

    station_node_ids: List[NodeId] = field(default_factory=list)
    current_station_idx: int = 0
    is_dwelling: bool = False
    dwell_ticks_remaining: int = 0

    def __post_init__(self) -> None:
        """Validate route-stop metadata and enforce BUS render identity."""
        if not self.station_node_ids:
            raise ValueError("PublicTransport requires at least one station node id.")

        self.vtype = VehicleType.BUS
        if not self.render_label:
            self.render_label = "BUS"
        if not self.render_color:
            self.render_color = VEHICLE_TYPE_CONFIGS[VehicleType.BUS].color or "#f39c12"

    @property
    def target_station_node_id(self) -> NodeId:
        """Return the active station target node id."""
        return self.station_node_ids[self.current_station_idx]

    def begin_station_dwell(self, rng: Optional[np.random.Generator] = None) -> int:
        """Start a station dwell window in the inclusive range [10, 20].

        Args:
            rng: Optional random generator for deterministic tests.

        Returns:
            Selected dwell duration in ticks.
        """
        generator = rng or np.random.default_rng()
        dwell_ticks = int(generator.integers(10, 21))
        self.is_dwelling = True
        self.dwell_ticks_remaining = dwell_ticks
        return dwell_ticks

    def tick_station_dwell(self) -> int:
        """Advance dwell countdown and clear dwelling state when complete.

        Returns:
            Remaining dwell ticks after decrement.
        """
        if not self.is_dwelling:
            self.dwell_ticks_remaining = max(0, int(self.dwell_ticks_remaining))
            return self.dwell_ticks_remaining

        self.dwell_ticks_remaining = max(0, int(self.dwell_ticks_remaining) - 1)
        if self.dwell_ticks_remaining == 0:
            self.is_dwelling = False

        return self.dwell_ticks_remaining

    def should_stop_for_node(self, node_id: NodeId) -> bool:
        """Return True when the given node matches the current station target."""
        return node_id == self.target_station_node_id

    def advance_station(self) -> None:
        """Advance to the next station target in a cyclic order."""
        self.current_station_idx = (self.current_station_idx + 1) % len(self.station_node_ids)


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
        lane_index: Current lane index for lane-aware rendering
        lateral_offset_m: Lateral offset in meters for lane-aware rendering
        render_label: Optional stable label for rendering overlays
        render_color: Optional stable color override for rendering overlays
    """
    vid: int
    vtype: VehicleType
    x: float
    y: float
    edge: EdgeId
    velocity: int
    speed_kmh: float
    wait_ticks: int
    lane_index: int = 0
    lateral_offset_m: float = 0.0
    render_label: Optional[str] = None
    render_color: Optional[str] = None
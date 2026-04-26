"""
Traffic light domain models for simulation.

Implements the traffic light logic from the prototype with NS/EW phase alternation,
offset-based coordination for green waves, and edge classification by bearing.
"""

from dataclasses import dataclass, field
from typing import Set
from .topology import EdgeId, NodeId


@dataclass
class TrafficLight:
    """
    Traffic light controller for intersection management.

    Based on TrafficLight class from prototype with NS/EW phase logic,
    configurable timing, and offset coordination for green wave effects.

    Attributes:
        node_id: Intersection node ID where light is located
        cycle_ticks: Total cycle duration in simulation ticks
        green_ratio: Fraction of cycle that NS phase is green (0.0-1.0)
        offset_ticks: Phase offset for coordination (0 to cycle_ticks-1)
        ns_edges: Set of north-south oriented incoming edges
        ew_edges: Set of east-west oriented incoming edges
    """
    node_id: NodeId
    cycle_ticks: int = 30
    green_ratio: float = 0.5
    offset_ticks: int = 0
    ns_edges: Set[EdgeId] = field(default_factory=set)
    ew_edges: Set[EdgeId] = field(default_factory=set)

    def is_green(self, edge_id: EdgeId, tick: int) -> bool:
        """
        Check if traffic light is green for the given edge at the given tick.

        Args:
            edge_id: Edge to check (must be incoming to this intersection)
            tick: Current simulation tick

        Returns:
            True if light is green for this edge, False if red

        Note:
            - NS edges are green during first part of cycle (0 to green_ratio * cycle)
            - EW edges are green during second part of cycle 
            - Edges not classified as NS or EW always return True (no light control)
        """
        phase_tick = (tick + self.offset_ticks) % self.cycle_ticks
        ns_green = phase_tick < int(self.cycle_ticks * self.green_ratio)

        if edge_id in self.ns_edges:
            return ns_green
        elif edge_id in self.ew_edges:
            return not ns_green
        else:
            return True  # No traffic light control for this edge
    
    def get_phase(self, tick: int) -> str:
        """
        Get current traffic light phase name.
        
        Args:
            tick: Current simulation tick
            
        Returns:
            "NS_GREEN" or "EW_GREEN" indicating which direction has green light
        """
        phase_tick = (tick + self.offset_ticks) % self.cycle_ticks
        ns_green = phase_tick < int(self.cycle_ticks * self.green_ratio)
        return "NS_GREEN" if ns_green else "EW_GREEN"
    
    def get_cycle_position(self, tick: int) -> float:
        """
        Get position within current cycle as fraction [0.0, 1.0).
        
        Args:
            tick: Current simulation tick
            
        Returns:
            Position within cycle (0.0 = start of cycle, 0.5 = halfway, etc.)
        """
        phase_tick = (tick + self.offset_ticks) % self.cycle_ticks
        return phase_tick / self.cycle_ticks


@dataclass
class LightState:
    """
    Snapshot of traffic light state for API responses and visualization.
    
    Attributes:
        node_id: Intersection node ID
        phase: Current phase ("NS_GREEN" or "EW_GREEN") 
        x: Geographic longitude of intersection
        y: Geographic latitude of intersection
        cycle_position: Position within cycle [0.0, 1.0)
        time_to_change: Ticks remaining until phase change
    """
    node_id: NodeId
    phase: str
    x: float
    y: float
    cycle_position: float
    time_to_change: int


def calculate_bearing(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Calculate bearing from point 1 to point 2 in degrees.
    
    Args:
        x1, y1: Coordinates of first point (typically node u)
        x2, y2: Coordinates of second point (typically node v)
        
    Returns:
        Bearing in degrees [0, 360), where 0° is north, 90° is east
    """
    import math
    dlat = y2 - y1
    dlon = x2 - x1
    return math.degrees(math.atan2(dlon, dlat)) % 360


def is_ns_orientation(bearing: float) -> bool:
    """
    Determine if bearing represents north-south orientation.
    
    Based on prototype bearing classification logic.
    
    Args:
        bearing: Bearing in degrees [0, 360)
        
    Returns:
        True if bearing is primarily north-south, False if east-west
        
    Note:
        - North-south: 315°-45° (north) or 135°-225° (south)  
        - East-west: 45°-135° (east) or 225°-315° (west)
    """
    return bearing < 45 or bearing > 315 or (135 < bearing < 225)
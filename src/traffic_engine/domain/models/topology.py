"""
Topology domain models for traffic simulation.

Defines the core data structures for representing the road network topology
in a format independent of NetworkX or OSMnx, suitable for the simulation engine.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


# Type aliases for clarity
NodeId = str
EdgeId = Tuple[NodeId, NodeId, int]  # (u, v, key) tuple
Coordinates = Tuple[float, float]    # (x, y) geographic coordinates


@dataclass
class NodeData:
    """
    Represents a node (intersection) in the road network.
    
    Attributes:
        x: Longitude (geographic x-coordinate)
        y: Latitude (geographic y-coordinate)
        is_boundary: True if node is on network perimeter (for inflow/outflow)
    """
    x: float
    y: float
    is_boundary: bool


@dataclass
class EdgeData:
    """
    Represents an edge (street segment) in the road network with discretization info.
    
    Attributes:
        length_m: Physical length in meters
        speed_kph: Speed limit in kilometers per hour
        n_cells: Number of discrete cells (length_m / CELL_SIZE_M)
        vmax_cells: Maximum velocity in cells per tick for this edge
        geometry_points: List of (x,y) points defining the edge shape
        n_lanes: Number of travel lanes available on this edge (minimum 1)
    """
    length_m: float
    speed_kph: float
    n_cells: int
    vmax_cells: int
    geometry_points: List[Coordinates]
    n_lanes: int = 1

    def __post_init__(self) -> None:
        """Normalize discretization values to safe minimums."""
        self.n_cells = max(1, int(self.n_cells))
        self.vmax_cells = max(1, int(self.vmax_cells))
        self.n_lanes = max(1, int(self.n_lanes))


@dataclass
class BoundingBox:
    """
    Geographic bounding box for the simulation area.
    
    Attributes:
        min_x: Minimum longitude
        max_x: Maximum longitude
        min_y: Minimum latitude
        max_y: Maximum latitude
    """
    min_x: float
    max_x: float
    min_y: float
    max_y: float


@dataclass
class TopologyData:
    """
    Complete road network topology data for simulation.
    
    This structure is independent of NetworkX/OSMnx and contains all information
    needed for the cellular automata simulation.
    
    Attributes:
        nodes: Dictionary mapping node IDs to node data
        edges: Dictionary mapping edge IDs to edge data
        bbox: Geographic bounding box of the network
    """
    nodes: Dict[NodeId, NodeData]
    edges: Dict[EdgeId, EdgeData]
    bbox: BoundingBox
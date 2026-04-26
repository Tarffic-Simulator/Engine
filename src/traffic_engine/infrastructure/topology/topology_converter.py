"""
Topology converter for NetworkX MultiDiGraph to TopologyData transformation.

Provides core functionality to convert an in-memory NetworkX graph into the 
domain-specific TopologyData structure required by the simulation engine.
"""

from typing import Any, Dict, List
import math

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None

from ...domain.models import (
    TopologyData, NodeData, EdgeData, BoundingBox,
    NodeId, EdgeId, Coordinates
)
from ...config.constants import CELL_SIZE_M
from .lane_defaults import resolve_edge_lane_count


class TopologyConverter:
    """
    Converts NetworkX MultiDiGraph to TopologyData for simulation.
    
    Handles the discretization of continuous road network data into the cellular
    automata grid format required by the NaSch model.
    """
    
    def __init__(self, cell_size_m: float = CELL_SIZE_M):
        """
        Initialize converter with cell size configuration.
        
        Args:
            cell_size_m: Size of each cell in meters (default from constants)
        """
        if not NETWORKX_AVAILABLE:
            raise ImportError("NetworkX is required for TopologyConverter")
            
        self.cell_size_m = cell_size_m
    
    def convert_graph(self, graph: 'nx.MultiDiGraph') -> TopologyData:
        """
        Convert NetworkX MultiDiGraph to TopologyData.
        
        Args:
            graph: NetworkX MultiDiGraph with 'length' and 'maxspeed' edge attributes
            
        Returns:
            TopologyData ready for simulation
            
        Raises:
            ValueError: If graph is invalid or missing required attributes
        """
        if not isinstance(graph, nx.MultiDiGraph):
            raise ValueError("Graph must be a NetworkX MultiDiGraph")
            
        if len(graph.nodes) == 0:
            raise ValueError("Graph cannot be empty")
        
        # Convert nodes
        nodes = self._convert_nodes(graph)
        
        # Convert edges with discretization
        edges = self._convert_edges(graph)
        
        # Calculate bounding box
        bbox = self._calculate_bbox(nodes)
        
        return TopologyData(
            nodes=nodes,
            edges=edges,
            bbox=bbox
        )
    
    def _convert_nodes(self, graph: 'nx.MultiDiGraph') -> Dict[NodeId, NodeData]:
        """Convert NetworkX nodes to NodeData."""
        nodes = {}
        
        # Identify boundary nodes (degree 1 for inflow/outflow)
        boundary_nodes = {
            node for node, degree in graph.degree() 
            if degree <= 2  # Conservative: include low-degree nodes as potential boundaries
        }
        
        for node_id in graph.nodes:
            node_attrs = graph.nodes[node_id]
            
            # Extract coordinates (OSMnx uses 'x', 'y' attributes)
            x = node_attrs.get('x', node_attrs.get('lon', 0.0))
            y = node_attrs.get('y', node_attrs.get('lat', 0.0))
            
            nodes[str(node_id)] = NodeData(
                x=float(x),
                y=float(y),
                is_boundary=(node_id in boundary_nodes)
            )
        
        return nodes
    
    def _convert_edges(self, graph: 'nx.MultiDiGraph') -> Dict[EdgeId, EdgeData]:
        """Convert NetworkX edges to EdgeData with discretization."""
        edges = {}
        
        for u, v, key in graph.edges(keys=True):
            edge_attrs = graph.edges[u, v, key]
            
            # Extract edge properties
            length_m = float(edge_attrs.get('length', 100.0))  # Default 100m
            speed_kph = self._parse_speed(self._get_speed_attribute(edge_attrs))
            n_lanes = resolve_edge_lane_count(
                raw_lanes=edge_attrs.get('lanes'),
                highway=edge_attrs.get('highway'),
            )
            
            # Discretize for cellular automata
            n_cells = max(1, int(math.ceil(length_m / self.cell_size_m)))
            vmax_cells = max(1, int(speed_kph * 1000 / 3600 / self.cell_size_m))  # Convert km/h to cells/s
            
            # Extract geometry if available
            geometry_points = self._extract_geometry(graph, u, v, key)
            
            edge_id = (str(u), str(v), key)
            edges[edge_id] = EdgeData(
                length_m=length_m,
                speed_kph=speed_kph,
                n_cells=n_cells,
                vmax_cells=vmax_cells,
                geometry_points=geometry_points,
                n_lanes=n_lanes,
            )
        
        return edges
    
    def _get_speed_attribute(self, edge_attrs: Dict[str, Any]) -> Any:
        """Get the raw speed attribute with prototype-compatible fallbacks."""
        if edge_attrs.get('maxspeed') is not None:
            return edge_attrs['maxspeed']
        if edge_attrs.get('speed_kph') is not None:
            return edge_attrs['speed_kph']
        return 50

    def _parse_speed(self, speed_attr: Any) -> float:
        """
        Parse speed attribute to float km/h.
        
        Handles various formats: "50", "50 mph", ["40", "50"], etc.
        """
        if isinstance(speed_attr, (int, float)):
            return float(speed_attr)
        
        if isinstance(speed_attr, str):
            # Extract numeric part
            try:
                return float(speed_attr.split()[0])
            except (ValueError, IndexError):
                return 50.0  # Default
        
        if isinstance(speed_attr, list) and len(speed_attr) > 0:
            try:
                return float(speed_attr[0])
            except (ValueError, TypeError):
                return 50.0
        
        return 50.0  # Default fallback
    
    def _extract_geometry(self, graph: 'nx.MultiDiGraph', u, v, key) -> List[Coordinates]:
        """Extract geometry points from edge, defaulting to node positions."""
        edge_attrs = graph.edges[u, v, key]
        
        # Check if geometry is available (from OSMnx)
        if 'geometry' in edge_attrs:
            try:
                geom = edge_attrs['geometry']
                if hasattr(geom, 'coords'):
                    return list(geom.coords)
            except Exception:
                pass
        
        # Fallback: use node coordinates
        u_node = graph.nodes[u]
        v_node = graph.nodes[v]
        
        u_x = u_node.get('x', u_node.get('lon', 0.0))
        u_y = u_node.get('y', u_node.get('lat', 0.0))
        v_x = v_node.get('x', v_node.get('lon', 0.0))
        v_y = v_node.get('y', v_node.get('lat', 0.0))
        
        return [(u_x, u_y), (v_x, v_y)]
    
    def _calculate_bbox(self, nodes: Dict[NodeId, NodeData]) -> BoundingBox:
        """Calculate bounding box from node coordinates."""
        if not nodes:
            return BoundingBox(min_x=0.0, max_x=0.0, min_y=0.0, max_y=0.0)
        
        x_coords = [node.x for node in nodes.values()]
        y_coords = [node.y for node in nodes.values()]
        
        return BoundingBox(
            min_x=min(x_coords),
            max_x=max(x_coords),
            min_y=min(y_coords),
            max_y=max(y_coords)
        )
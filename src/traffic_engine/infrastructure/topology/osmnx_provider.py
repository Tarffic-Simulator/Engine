"""
OSMnx topology provider for loading road networks from OpenStreetMap.

Provides topology data by interfacing with OSMnx to download and process
road network data from OpenStreetMap, with appropriate error handling
and import guards for optional dependencies.
"""

from typing import Any, Callable, Optional
import logging

# Import guard for optional dependencies
try:
    import osmnx as ox
    import networkx as nx
    OSMNX_AVAILABLE = True
except ImportError:
    OSMNX_AVAILABLE = False
    ox = None
    nx = None

from ...domain.models import TopologyData, BoundingBox
from ...application.contracts import TopologyProvider
from .topology_converter import TopologyConverter

logger = logging.getLogger(__name__)


def _resolve_add_edge_lengths() -> Callable[..., Any]:
    """Return the OSMnx edge-length helper across supported API layouts."""
    add_edge_lengths = getattr(ox, 'add_edge_lengths', None)
    if callable(add_edge_lengths):
        return add_edge_lengths

    distance_module = getattr(ox, 'distance', None)
    add_edge_lengths = getattr(distance_module, 'add_edge_lengths', None)
    if callable(add_edge_lengths):
        return add_edge_lengths

    raise AttributeError("OSMnx installation does not expose add_edge_lengths.")


def _resolve_add_edge_speeds() -> Callable[..., Any]:
    """Return the OSMnx edge-speed helper across supported API layouts."""
    add_edge_speeds = getattr(ox, 'add_edge_speeds', None)
    if callable(add_edge_speeds):
        return add_edge_speeds

    routing_module = getattr(ox, 'routing', None)
    add_edge_speeds = getattr(routing_module, 'add_edge_speeds', None)
    if callable(add_edge_speeds):
        return add_edge_speeds

    raise AttributeError("OSMnx installation does not expose add_edge_speeds.")


class OSMnxTopologyProvider:
    """
    Topology provider using OSMnx for OpenStreetMap data.
    
    Downloads road network data from OpenStreetMap and converts it to
    the simulation engine's TopologyData format.
    """
    
    def __init__(self, converter: Optional[TopologyConverter] = None):
        """
        Initialize OSMnx provider.
        
        Args:
            converter: TopologyConverter instance (creates default if None)
            
        Raises:
            ImportError: If OSMnx is not available
        """
        if not OSMNX_AVAILABLE:
            raise ImportError(
                "OSMnx and NetworkX are required for OSMnxTopologyProvider. "
                "Install with: pip install osmnx networkx"
            )
        
        self.converter = converter or TopologyConverter()
        
        # Configure OSMnx for traffic simulation
        ox.settings.log_console = True
        ox.settings.use_cache = True
    
    def load_area(self, area: str) -> TopologyData:
        """
        Load topology data for a named geographic area.
        
        Args:
            area: Area name (e.g., "Roma Norte, Ciudad de México")
            
        Returns:
            Complete topology data ready for simulation
            
        Raises:
            ValueError: If area name is invalid or not found
            ConnectionError: If OpenStreetMap is unavailable
        """
        logger.info(f"Loading road network for area: {area}")
        
        try:
            # Download road network from OpenStreetMap
            graph = ox.graph_from_place(
                area, 
                network_type='drive',
                simplify=True,
                retain_all=False
            )
            
            # Add missing edge attributes for simulation
            graph = self._prepare_graph(graph)
            
            logger.info(
                f"Downloaded network: {len(graph.nodes)} nodes, "
                f"{len(graph.edges)} edges"
            )
            
            # Convert to simulation format
            return self.converter.convert_graph(graph)
            
        except Exception as e:
            if "not found" in str(e).lower():
                raise ValueError(f"Area '{area}' not found in OpenStreetMap") from e
            else:
                raise ConnectionError(f"Failed to download area '{area}': {e}") from e
    
    def load_bbox(self, bbox: BoundingBox) -> TopologyData:
        """
        Load topology data for a geographic bounding box.
        
        Args:
            bbox: Geographic bounding box
            
        Returns:
            Complete topology data ready for simulation
            
        Raises:
            ValueError: If bounding box is invalid
            ConnectionError: If OpenStreetMap is unavailable
        """
        logger.info(
            f"Loading road network for bbox: "
            f"({bbox.min_y}, {bbox.min_x}) to ({bbox.max_y}, {bbox.max_x})"
        )
        
        # Validate bounding box
        if bbox.min_x >= bbox.max_x or bbox.min_y >= bbox.max_y:
            raise ValueError("Invalid bounding box: min values must be < max values")
        
        try:
            # Download road network from bounding box
            graph = ox.graph_from_bbox(
                bbox.max_y, bbox.min_y, bbox.max_x, bbox.min_x,
                network_type='drive',
                simplify=True,
                retain_all=False
            )
            
            # Add missing edge attributes for simulation
            graph = self._prepare_graph(graph)
            
            logger.info(
                f"Downloaded network: {len(graph.nodes)} nodes, "
                f"{len(graph.edges)} edges"
            )
            
            # Convert to simulation format
            return self.converter.convert_graph(graph)
            
        except Exception as e:
            raise ConnectionError(f"Failed to download bounding box: {e}") from e
    
    def _prepare_graph(self, graph: 'nx.MultiDiGraph') -> 'nx.MultiDiGraph':
        """
        Prepare graph for simulation by adding missing attributes.
        
        Args:
            graph: Raw graph from OSMnx
            
        Returns:
            Graph with required attributes for simulation
        """
        add_edge_lengths = _resolve_add_edge_lengths()
        add_edge_speeds = _resolve_add_edge_speeds()

        # Add edge lengths if missing
        graph = add_edge_lengths(graph)
        
        # Add speed attributes if missing
        graph = add_edge_speeds(graph)
        
        # Ensure all edges have required attributes
        for u, v, key in graph.edges(keys=True):
            edge = graph.edges[u, v, key]
            
            # Set default length if missing
            if 'length' not in edge or edge['length'] <= 0:
                edge['length'] = 100.0  # Default 100m
            
            # Set default speed if missing
            if 'maxspeed' not in edge:
                edge['maxspeed'] = 50  # Default 50 km/h
        
        return graph
"""
Centrality-based traffic light provider using betweenness centrality.

Places traffic lights at intersections with high betweenness centrality,
mimicking real-world placement strategies where lights are installed at
critical traffic flow points.
"""

from typing import List, Dict, Any, Set, Tuple
import logging

# Import guard for NetworkX (optional dependency)
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None

from ...domain.models import (
    TopologyData, TrafficLight, EdgeId, NodeId,
    calculate_bearing, is_ns_orientation
)
from ...application.contracts import TrafficLightProvider

logger = logging.getLogger(__name__)


class CentralityTrafficLightProvider:
    """
    Traffic light provider using betweenness centrality for placement.
    
    Identifies critical intersections by calculating betweenness centrality
    and places traffic lights at the most important flow control points.
    """
    
    def __init__(
        self,
        centrality_threshold: float = 0.01,
        min_edges_for_light: int = 3,
        max_lights: int = 50,
        cycle_ticks: int = 30,
        green_ratio: float = 0.5,
        offset_strategy: str = "uniform"  # "uniform" or "distance"
    ):
        """
        Initialize centrality-based provider.
        
        Args:
            centrality_threshold: Minimum centrality score to place a light
            min_edges_for_light: Minimum incoming edges required
            max_lights: Maximum number of lights to place
            cycle_ticks: Default cycle duration in ticks
            green_ratio: Default NS green phase ratio
            offset_strategy: Strategy for offset calculation ("uniform" or "distance")
        """
        if not NETWORKX_AVAILABLE:
            raise ImportError("NetworkX is required for CentralityTrafficLightProvider")
        
        self.centrality_threshold = centrality_threshold
        self.min_edges_for_light = min_edges_for_light
        self.max_lights = max_lights
        self.cycle_ticks = cycle_ticks
        self.green_ratio = green_ratio
        self.offset_strategy = offset_strategy
        self._light_configs: Dict[str, Dict[str, Any]] = {}
    
    def get_lights(self, topology: TopologyData) -> List[TrafficLight]:
        """
        Generate traffic lights using betweenness centrality analysis.
        
        Args:
            topology: Road network topology data
            
        Returns:
            List of traffic lights at high-centrality intersections
        """
        logger.info(f"Computing centrality-based traffic lights for {len(topology.nodes)} nodes")
        
        # Convert topology to NetworkX for centrality analysis
        graph = self._topology_to_networkx(topology)
        
        # Calculate betweenness centrality
        centrality = nx.betweenness_centrality(graph, normalized=True)
        
        # Find intersection edges
        intersection_edges = self._find_intersection_edges(topology)
        
        # Select nodes for traffic lights based on centrality
        candidate_nodes = []
        for node_id, score in centrality.items():
            if (score >= self.centrality_threshold and 
                node_id in intersection_edges and
                len(intersection_edges[node_id]) >= self.min_edges_for_light):
                candidate_nodes.append((node_id, score))
        
        # Sort by centrality and take top candidates
        candidate_nodes.sort(key=lambda x: x[1], reverse=True)
        selected_nodes = candidate_nodes[:self.max_lights]
        
        logger.info(f"Selected {len(selected_nodes)} high-centrality intersections")
        
        # Create traffic lights with coordinated offsets
        lights = []
        for i, (node_id, centrality_score) in enumerate(selected_nodes):
            incoming_edges = intersection_edges[node_id]
            offset = self._calculate_offset(node_id, i, topology, selected_nodes)
            
            # Get custom config if available
            config = self._light_configs.get(node_id, {})
            
            light = self._create_light(
                node_id,
                incoming_edges,
                topology,
                offset,
                config,
                centrality_score
            )
            
            lights.append(light)
        
        logger.info(f"Created {len(lights)} centrality-based traffic lights")
        return lights
    
    def update_config(self, light_id: str, config: Dict[str, Any]) -> None:
        """Update configuration for specific traffic light."""
        self._light_configs[light_id] = config
        logger.info(f"Updated config for traffic light {light_id}: {config}")
    
    def _topology_to_networkx(self, topology: TopologyData) -> 'nx.DiGraph':
        """Convert TopologyData to NetworkX DiGraph for centrality analysis."""
        graph = nx.DiGraph()
        
        # Add nodes
        for node_id, node_data in topology.nodes.items():
            graph.add_node(node_id, x=node_data.x, y=node_data.y)
        
        # Add edges (simplified to DiGraph for centrality calculation)
        for edge_id, edge_data in topology.edges.items():
            u, v, key = edge_id
            # Use length as weight for shortest path calculations
            graph.add_edge(u, v, weight=edge_data.length_m)
        
        return graph
    
    def _find_intersection_edges(self, topology: TopologyData) -> Dict[NodeId, List[EdgeId]]:
        """Find incoming edges for each intersection node."""
        intersection_edges: Dict[NodeId, List[EdgeId]] = {}
        
        for edge_id, edge_data in topology.edges.items():
            u, v, key = edge_id
            target_node = v
            
            if target_node not in intersection_edges:
                intersection_edges[target_node] = []
            
            intersection_edges[target_node].append(edge_id)
        
        return intersection_edges
    
    def _calculate_offset(
        self, 
        node_id: NodeId, 
        index: int, 
        topology: TopologyData,
        selected_nodes: List[Tuple[NodeId, float]]
    ) -> int:
        """Calculate offset for traffic light coordination."""
        
        if self.offset_strategy == "uniform":
            # Uniform distribution of offsets
            return (index * self.cycle_ticks // len(selected_nodes)) % self.cycle_ticks
        
        elif self.offset_strategy == "distance":
            # Distance-based offset (simplified green wave approximation)
            if index == 0:
                return 0
            
            # Find nearest previous light and estimate travel time
            node_pos = topology.nodes[node_id]
            min_distance = float('inf')
            
            for prev_node_id, _ in selected_nodes[:index]:
                prev_pos = topology.nodes[prev_node_id]
                distance = ((node_pos.x - prev_pos.x)**2 + (node_pos.y - prev_pos.y)**2)**0.5
                min_distance = min(min_distance, distance)
            
            # Estimate travel time (assuming ~50 km/h average speed)
            travel_time_s = min_distance / (50 * 1000 / 3600)  # Convert to seconds
            travel_time_ticks = int(travel_time_s)  # Assuming 1 tick = 1 second
            
            return travel_time_ticks % self.cycle_ticks
        
        else:
            return 0
    
    def _create_light(
        self,
        node_id: NodeId,
        incoming_edges: List[EdgeId],
        topology: TopologyData,
        offset: int,
        custom_config: Dict[str, Any],
        centrality_score: float
    ) -> TrafficLight:
        """Create traffic light with edge classification."""
        
        # Classify edges by bearing
        ns_edges: Set[EdgeId] = set()
        ew_edges: Set[EdgeId] = set()
        
        node_data = topology.nodes[node_id]
        
        for edge_id in incoming_edges:
            u, v, key = edge_id
            source_node = topology.nodes[u]
            
            bearing = calculate_bearing(
                source_node.x, source_node.y,
                node_data.x, node_data.y
            )
            
            if is_ns_orientation(bearing):
                ns_edges.add(edge_id)
            else:
                ew_edges.add(edge_id)
        
        # Apply custom config or defaults
        cycle_ticks = custom_config.get('cycle_ticks', self.cycle_ticks)
        green_ratio = custom_config.get('green_ratio', self.green_ratio)
        offset_ticks = custom_config.get('offset_ticks', offset)
        
        # Adjust timing based on centrality (higher centrality = longer cycle)
        if 'cycle_ticks' not in custom_config and centrality_score > 0.05:
            cycle_ticks = int(self.cycle_ticks * 1.2)  # 20% longer for high-centrality nodes
        
        return TrafficLight(
            node_id=node_id,
            cycle_ticks=cycle_ticks,
            green_ratio=green_ratio,
            offset_ticks=offset_ticks,
            ns_edges=ns_edges,
            ew_edges=ew_edges
        )
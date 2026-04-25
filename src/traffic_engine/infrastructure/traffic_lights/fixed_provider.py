"""
Fixed traffic light provider for deterministic configurations.

Provides simple, fixed traffic light configurations for testing and 
basic simulation scenarios without requiring complex placement algorithms.
"""

from typing import List, Dict, Any, Set
import logging

from ...domain.models import (
    TopologyData, TrafficLight, EdgeId, NodeId,
    calculate_bearing, is_ns_orientation
)
from ...application.contracts import TrafficLightProvider

logger = logging.getLogger(__name__)


class FixedTrafficLightProvider:
    """
    Traffic light provider with fixed, configurable placement rules.
    
    Provides deterministic traffic light placement based on simple
    intersection criteria and configurable timing parameters.
    """
    
    def __init__(
        self,
        min_edges_for_light: int = 3,
        cycle_ticks: int = 30,
        green_ratio: float = 0.5,
        offset_increment: int = 10
    ):
        """
        Initialize fixed provider with configuration.
        
        Args:
            min_edges_for_light: Minimum incoming edges to place a light
            cycle_ticks: Default cycle duration in simulation ticks
            green_ratio: Fraction of cycle for NS green phase
            offset_increment: Offset increment between adjacent lights
        """
        self.min_edges_for_light = min_edges_for_light
        self.cycle_ticks = cycle_ticks
        self.green_ratio = green_ratio
        self.offset_increment = offset_increment
        self._light_configs: Dict[str, Dict[str, Any]] = {}
    
    def get_lights(self, topology: TopologyData) -> List[TrafficLight]:
        """
        Generate traffic lights for intersections meeting criteria.
        
        Args:
            topology: Road network topology data
            
        Returns:
            List of configured traffic lights for qualifying intersections
        """
        logger.info(f"Generating fixed traffic lights for {len(topology.nodes)} nodes")
        
        # Find intersections (nodes with multiple incoming edges)
        intersection_edges = self._find_intersection_edges(topology)
        
        lights = []
        current_offset = 0
        
        for node_id, incoming_edges in intersection_edges.items():
            if len(incoming_edges) >= self.min_edges_for_light:
                # Get custom config if available
                config = self._light_configs.get(node_id, {})
                
                light = self._create_light(
                    node_id, 
                    incoming_edges, 
                    topology,
                    current_offset,
                    config
                )
                
                lights.append(light)
                current_offset = (current_offset + self.offset_increment) % self.cycle_ticks
        
        logger.info(f"Created {len(lights)} traffic lights")
        return lights
    
    def update_config(self, light_id: str, config: Dict[str, Any]) -> None:
        """
        Update configuration for specific traffic light.
        
        Args:
            light_id: Traffic light identifier (node_id)
            config: New configuration parameters (cycle_ticks, green_ratio, etc.)
        """
        self._light_configs[light_id] = config
        logger.info(f"Updated config for traffic light {light_id}: {config}")
    
    def _find_intersection_edges(self, topology: TopologyData) -> Dict[NodeId, List[EdgeId]]:
        """Find incoming edges for each intersection node."""
        intersection_edges: Dict[NodeId, List[EdgeId]] = {}
        
        for edge_id, edge_data in topology.edges.items():
            u, v, key = edge_id
            target_node = v  # Target node of the edge
            
            if target_node not in intersection_edges:
                intersection_edges[target_node] = []
            
            intersection_edges[target_node].append(edge_id)
        
        return intersection_edges
    
    def _create_light(
        self, 
        node_id: NodeId, 
        incoming_edges: List[EdgeId],
        topology: TopologyData,
        default_offset: int,
        custom_config: Dict[str, Any]
    ) -> TrafficLight:
        """Create traffic light with edge classification and custom config."""
        
        # Classify edges by bearing
        ns_edges: Set[EdgeId] = set()
        ew_edges: Set[EdgeId] = set()
        
        node_data = topology.nodes[node_id]
        
        for edge_id in incoming_edges:
            u, v, key = edge_id
            source_node = topology.nodes[u]
            
            # Calculate bearing from source to target
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
        offset_ticks = custom_config.get('offset_ticks', default_offset)
        
        return TrafficLight(
            node_id=node_id,
            cycle_ticks=cycle_ticks,
            green_ratio=green_ratio,
            offset_ticks=offset_ticks,
            ns_edges=ns_edges,
            ew_edges=ew_edges
        )
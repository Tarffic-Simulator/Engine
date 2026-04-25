"""
Provider interfaces for external data sources.

Defines the contracts that external data providers must implement,
enabling pluggable topology and traffic light data sources.
"""

from typing import Protocol, List, Dict, Any
from ...domain.models import TopologyData, TrafficLight, BoundingBox


class TopologyProvider(Protocol):
    """
    Protocol for topology data providers.
    
    Implementations can load road network data from various sources:
    - OSMnx for OpenStreetMap data
    - Database for cached/processed networks
    - Mock/synthetic for testing
    """
    
    def load_area(self, area: str) -> TopologyData:
        """
        Load topology data for a named geographic area.
        
        Args:
            area: Area name (e.g., "Roma Norte, Ciudad de México")
            
        Returns:
            Complete topology data ready for simulation
            
        Raises:
            ValueError: If area name is invalid or not found
            ConnectionError: If data source is unavailable
        """
        ...
    
    def load_bbox(self, bbox: BoundingBox) -> TopologyData:
        """
        Load topology data for a geographic bounding box.
        
        Args:
            bbox: Geographic bounding box
            
        Returns:
            Complete topology data ready for simulation
            
        Raises:
            ValueError: If bounding box is invalid
            ConnectionError: If data source is unavailable  
        """
        ...


class TrafficLightProvider(Protocol):
    """
    Protocol for traffic light configuration providers.
    
    Implementations can determine traffic light placement and timing:
    - Centrality-based inference from topology
    - Real traffic control data from city systems
    - Manual configuration for testing
    """
    
    def get_lights(self, topology: TopologyData) -> List[TrafficLight]:
        """
        Generate traffic light configurations for the given topology.
        
        Args:
            topology: Road network topology data
            
        Returns:
            List of configured traffic lights for intersections
            
        Note:
            Traffic lights should have properly classified NS/EW edges
            and reasonable timing parameters for urban traffic.
        """
        ...
    
    def update_config(self, light_id: str, config: Dict[str, Any]) -> None:
        """
        Update configuration for specific traffic light.
        
        Args:
            light_id: Traffic light identifier (node_id)
            config: New configuration parameters
            
        Note:
            This method allows runtime adjustment of traffic light timing
            for optimization or real-time control scenarios.
        """
        ...
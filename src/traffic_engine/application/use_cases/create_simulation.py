"""
CreateSimulation use case implementation.

Orchestrates the creation of a new traffic simulation by coordinating
topology loading, traffic light configuration, and model initialization.
"""

from typing import Optional
import logging

from ..contracts import (
    CreateSimulationRequest, CreateSimulationResponse, SimulationConfigDto,
    TopologyProvider, TrafficLightProvider
)
from ...domain.simulation import SimulationModel
from ...domain.models import TopologyData, BoundingBox


logger = logging.getLogger(__name__)


class CreateSimulationUseCase:
    """
    Use case for creating new traffic simulations.
    
    Coordinates the complex process of setting up a simulation:
    1. Load topology data from provider
    2. Configure traffic lights for intersections  
    3. Initialize simulation model with topology
    4. Apply configuration overrides
    5. Return initialized simulation ready for stepping
    """
    
    def __init__(
        self,
        topology_provider: TopologyProvider,
        traffic_light_provider: TrafficLightProvider,
        simulation_model: SimulationModel
    ):
        """
        Initialize use case with required providers.
        
        Args:
            topology_provider: Source for road network data
            traffic_light_provider: Source for traffic light configuration
            simulation_model: Simulation engine to initialize
        """
        self.topology_provider = topology_provider
        self.traffic_light_provider = traffic_light_provider
        self.simulation_model = simulation_model
    
    def execute(self, request: CreateSimulationRequest) -> CreateSimulationResponse:
        """
        Execute simulation creation use case.
        
        Args:
            request: Simulation creation parameters
            
        Returns:
            Response with simulation ID and initial state, or error details
        """
        try:
            # Load topology data
            logger.info(f"Loading topology for request: area={request.area}, bbox={request.bbox}")
            topology = self._load_topology(request)
            
            # Configure traffic lights
            logger.info("Configuring traffic lights")
            traffic_lights = self.traffic_light_provider.get_lights(topology)
            
            # Prepare simulation configuration
            config = self._prepare_config(request.config)
            
            # Initialize simulation model
            logger.info("Initializing simulation model")
            initial_state = self.simulation_model.reset(topology, config)
            
            # Add traffic lights to simulation
            for light in traffic_lights:
                self.simulation_model.add_traffic_light(light)
            
            # Generate simulation ID (would use UUID in production)
            import uuid
            simulation_id = str(uuid.uuid4())
            
            # Prepare response
            return CreateSimulationResponse(
                simulation_id=simulation_id,
                initial_state=self._state_to_dict(initial_state),
                topology_summary=self._topology_summary(topology),
                traffic_lights_count=len(traffic_lights),
                success=True
            )
            
        except ValueError as e:
            logger.warning(f"Validation error creating simulation: {e}")
            return CreateSimulationResponse(
                simulation_id="",
                initial_state={},
                topology_summary={},
                traffic_lights_count=0,
                success=False,
                error=f"Validation error: {str(e)}"
            )
        
        except ConnectionError as e:
            logger.error(f"Connection error loading data: {e}")
            return CreateSimulationResponse(
                simulation_id="",
                initial_state={},
                topology_summary={},
                traffic_lights_count=0,
                success=False,
                error=f"Data loading failed: {str(e)}"
            )
        
        except Exception as e:
            logger.error(f"Unexpected error creating simulation: {e}")
            return CreateSimulationResponse(
                simulation_id="",
                initial_state={},
                topology_summary={},
                traffic_lights_count=0,
                success=False,
                error=f"Internal error: {str(e)}"
            )
    
    def _load_topology(self, request: CreateSimulationRequest) -> TopologyData:
        """Load topology data based on request type."""
        if request.area:
            return self.topology_provider.load_area(request.area)
        elif request.bbox:
            return self.topology_provider.load_bbox(request.bbox)
        else:
            raise ValueError("Request must specify either area or bbox")
    
    def _prepare_config(self, request_config: Optional[dict]) -> dict:
        """Prepare simulation configuration with defaults and validation."""
        # Start with default configuration
        config = {
            'initial_vehicles': 0,
            'max_vehicles': 1000,
            'spawn_rate': 0.1,
            'noise_prob': 0.28,
            'timeout_ticks': 50,
            'max_ticks': 10000,
        }
        
        # Apply overrides from request
        if request_config:
            config.update(request_config)
        
        # Validate configuration
        self._validate_config(config)
        
        return config
    
    def _validate_config(self, config: dict):
        """Validate simulation configuration parameters."""
        if config.get('initial_vehicles', 0) < 0:
            raise ValueError("initial_vehicles must be non-negative")
        
        if config.get('max_vehicles', 1000) < 1:
            raise ValueError("max_vehicles must be positive")
        
        noise_prob = config.get('noise_prob', 0.28)
        if not (0 <= noise_prob <= 1):
            raise ValueError("noise_prob must be between 0 and 1")
        
        spawn_rate = config.get('spawn_rate', 0.1)
        if spawn_rate < 0:
            raise ValueError("spawn_rate must be non-negative")
        
        if config.get('timeout_ticks', 50) < 1:
            raise ValueError("timeout_ticks must be positive")
    
    def _state_to_dict(self, state) -> dict:
        """Convert simulation state to dictionary for response."""
        return {
            'tick': state.tick,
            'total_vehicles': state.total_vehicles,
            'active_vehicles': state.active_vehicles,
            'vehicle_count': len(state.vehicles),
            'traffic_light_count': len(state.traffic_lights)
        }
    
    def _topology_summary(self, topology: TopologyData) -> dict:
        """Generate topology summary for response."""
        return {
            'nodes_count': len(topology.nodes),
            'edges_count': len(topology.edges),
            'bbox': {
                'min_x': topology.bbox.min_x,
                'max_x': topology.bbox.max_x,
                'min_y': topology.bbox.min_y,
                'max_y': topology.bbox.max_y,
            },
            'boundary_nodes': sum(1 for node in topology.nodes.values() if node.is_boundary),
            'total_cells': sum(edge.n_cells for edge in topology.edges.values()),
            'avg_edge_length_m': sum(edge.length_m for edge in topology.edges.values()) / len(topology.edges) if topology.edges else 0,
        }
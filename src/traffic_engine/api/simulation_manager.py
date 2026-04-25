"""Simulation manager for handling multiple concurrent simulations."""

import logging
from typing import Dict, Optional, Any
from uuid import uuid4
from threading import Lock
import time

from ..domain.simulation import SimulationModel, NaSchSimulationModel
from ..application.use_cases import (
    CreateSimulationUseCase, StepSimulationUseCase, 
    GetMetricsUseCase, GetSnapshotUseCase
)
from ..application.contracts import (
    CreateSimulationRequest, CreateSimulationResponse,
    StepSimulationRequest, StepSimulationResponse,
    GetMetricsRequest, GetMetricsResponse,
    GetSnapshotRequest, GetSnapshotResponse,
    TopologyProvider, TrafficLightProvider
)
from ..infrastructure.topology import OSMNX_AVAILABLE, OSMnxTopologyProvider
from ..infrastructure.traffic_lights import FixedTrafficLightProvider

logger = logging.getLogger(__name__)


class SimulationInstance:
    """
    Container for a single simulation instance and its associated use cases.
    """
    
    def __init__(
        self,
        simulation_id: str,
        simulation_model: SimulationModel,
        topology_provider: TopologyProvider,
        traffic_light_provider: TrafficLightProvider
    ):
        self.simulation_id = simulation_id
        self.simulation_model = simulation_model
        self.created_at = time.time()
        self.last_accessed = time.time()
        
        # Initialize use cases
        self.create_use_case = CreateSimulationUseCase(
            topology_provider, traffic_light_provider, simulation_model
        )
        self.step_use_case = StepSimulationUseCase(simulation_model)
        self.metrics_use_case = GetMetricsUseCase(simulation_model)
        self.snapshot_use_case = GetSnapshotUseCase(simulation_model)
        
        # State tracking
        self.is_initialized = False
        self.is_completed = False
    
    def touch(self):
        """Update last accessed time."""
        self.last_accessed = time.time()


class SimulationManager:
    """
    Manager for multiple concurrent traffic simulations.
    
    Handles creation, retrieval, and lifecycle management of simulation instances
    for the REST API, including resource cleanup and session management.
    """
    
    def __init__(
        self,
        default_topology_provider: Optional[TopologyProvider] = None,
        default_traffic_light_provider: Optional[TrafficLightProvider] = None,
        max_concurrent_simulations: int = 10,
        cleanup_interval_s: float = 300.0,  # 5 minutes
        instance_timeout_s: float = 3600.0   # 1 hour
    ):
        """
        Initialize simulation manager.
        
        Args:
            default_topology_provider: Default topology data source
            default_traffic_light_provider: Default traffic light provider
            max_concurrent_simulations: Maximum concurrent simulation instances
            cleanup_interval_s: Interval for automatic cleanup in seconds
            instance_timeout_s: Timeout for unused instances in seconds
        """
        self.default_topology_provider = default_topology_provider or self._get_default_topology_provider()
        self.default_traffic_light_provider = default_traffic_light_provider or FixedTrafficLightProvider()
        self.max_concurrent_simulations = max_concurrent_simulations
        self.cleanup_interval_s = cleanup_interval_s
        self.instance_timeout_s = instance_timeout_s
        
        # Instance storage and synchronization
        self._instances: Dict[str, SimulationInstance] = {}
        self._lock = Lock()
        self._last_cleanup = time.time()
        
        logger.info(f"SimulationManager initialized with max {max_concurrent_simulations} concurrent simulations")
    
    def create_simulation(self, request: CreateSimulationRequest) -> CreateSimulationResponse:
        """
        Create a new simulation instance.
        
        Args:
            request: Simulation creation parameters
            
        Returns:
            Response with simulation ID and initial state
        """
        with self._lock:
            # Check instance limits
            if len(self._instances) >= self.max_concurrent_simulations:
                self._cleanup_expired_instances()
                if len(self._instances) >= self.max_concurrent_simulations:
                    return CreateSimulationResponse(
                        simulation_id="",
                        initial_state={},
                        topology_summary={},
                        traffic_lights_count=0,
                        success=False,
                        error="Maximum concurrent simulations reached"
                    )
            
            # Generate unique simulation ID
            simulation_id = str(uuid4())
            
            # Create simulation model instance
            simulation_model = NaSchSimulationModel()
            
            # Create simulation instance
            instance = SimulationInstance(
                simulation_id=simulation_id,
                simulation_model=simulation_model,
                topology_provider=self.default_topology_provider,
                traffic_light_provider=self.default_traffic_light_provider
            )
            
            # Execute creation use case
            response = instance.create_use_case.execute(request)
            
            if response.success:
                # Store instance
                instance.is_initialized = True
                instance.touch()
                self._instances[simulation_id] = instance
                
                logger.info(f"Created simulation {simulation_id}")
                # Fix dataclass assignment (not namedtuple _replace)
                response.simulation_id = simulation_id
                return response
            else:
                logger.warning(f"Failed to create simulation: {response.error}")
                return response
    
    def step_simulation(
        self, 
        simulation_id: str, 
        request: StepSimulationRequest
    ) -> StepSimulationResponse:
        """
        Step an existing simulation.
        
        Args:
            simulation_id: Simulation identifier
            request: Step parameters
            
        Returns:
            Response with updated state and metrics
        """
        instance = self._get_instance(simulation_id)
        if not instance:
            return StepSimulationResponse(
                simulation_id=simulation_id,
                new_tick=-1,
                metrics={},
                vehicles_spawned=0,
                vehicles_removed=0,
                success=False,
                error="Simulation not found"
            )
        
        instance.touch()
        response = instance.step_use_case.execute(simulation_id, request)
        
        # Check if simulation completed
        if response.success and hasattr(instance.simulation_model, 'is_done'):
            instance.is_completed = instance.simulation_model.is_done()
        
        return response
    
    def get_metrics(
        self, 
        simulation_id: str, 
        request: GetMetricsRequest
    ) -> GetMetricsResponse:
        """
        Get metrics for an existing simulation.
        
        Args:
            simulation_id: Simulation identifier
            request: Metrics request parameters
            
        Returns:
            Response with simulation metrics
        """
        instance = self._get_instance(simulation_id)
        if not instance:
            return GetMetricsResponse(
                simulation_id=simulation_id,
                current_metrics={},
                success=False,
                error="Simulation not found"
            )
        
        instance.touch()
        return instance.metrics_use_case.execute(simulation_id, request)
    
    def get_snapshot(
        self, 
        simulation_id: str, 
        request: GetSnapshotRequest
    ) -> GetSnapshotResponse:
        """
        Get detailed snapshot for an existing simulation.
        
        Args:
            simulation_id: Simulation identifier
            request: Snapshot request parameters
            
        Returns:
            Response with detailed simulation snapshot
        """
        instance = self._get_instance(simulation_id)
        if not instance:
            return GetSnapshotResponse(
                simulation_id=simulation_id,
                snapshot={},
                success=False,
                error="Simulation not found"
            )
        
        instance.touch()
        return instance.snapshot_use_case.execute(simulation_id, request)
    
    def delete_simulation(self, simulation_id: str) -> bool:
        """
        Delete a simulation instance.
        
        Args:
            simulation_id: Simulation identifier
            
        Returns:
            True if deleted successfully, False if not found
        """
        with self._lock:
            if simulation_id in self._instances:
                del self._instances[simulation_id]
                logger.info(f"Deleted simulation {simulation_id}")
                return True
            return False
    
    def list_simulations(self) -> Dict[str, Dict[str, Any]]:
        """
        List all active simulations with basic info.
        
        Returns:
            Dictionary mapping simulation IDs to basic info
        """
        with self._lock:
            return {
                sim_id: {
                    'created_at': instance.created_at,
                    'last_accessed': instance.last_accessed,
                    'is_initialized': instance.is_initialized,
                    'is_completed': instance.is_completed,
                }
                for sim_id, instance in self._instances.items()
            }
    
    def _get_instance(self, simulation_id: str) -> Optional[SimulationInstance]:
        """Get simulation instance by ID with automatic cleanup."""
        with self._lock:
            # Periodic cleanup
            current_time = time.time()
            if current_time - self._last_cleanup > self.cleanup_interval_s:
                self._cleanup_expired_instances()
            
            return self._instances.get(simulation_id)
    
    def _cleanup_expired_instances(self):
        """Remove expired simulation instances."""
        current_time = time.time()
        expired_ids = []
        
        for sim_id, instance in self._instances.items():
            if (current_time - instance.last_accessed) > self.instance_timeout_s:
                expired_ids.append(sim_id)
        
        for sim_id in expired_ids:
            del self._instances[sim_id]
            logger.info(f"Cleaned up expired simulation {sim_id}")
        
        self._last_cleanup = current_time
        
        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired simulations")
    
    def _get_default_topology_provider(self) -> TopologyProvider:
        """Get default topology provider with fallback."""
        if OSMNX_AVAILABLE:
            try:
                return OSMnxTopologyProvider()
            except Exception as exc:
                logger.warning("OSMnx provider unavailable, using mock topology provider: %s", exc)

        logger.warning("OSMnx not available, using mock topology provider")
        return MockTopologyProvider()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        with self._lock:
            active_count = len(self._instances)
            initialized_count = sum(1 for i in self._instances.values() if i.is_initialized)
            completed_count = sum(1 for i in self._instances.values() if i.is_completed)
            
            return {
                'active_simulations': active_count,
                'initialized_simulations': initialized_count,
                'completed_simulations': completed_count,
                'max_concurrent': self.max_concurrent_simulations,
                'last_cleanup': self._last_cleanup,
            }


class MockTopologyProvider:
    """Mock topology provider for testing when OSMnx is unavailable."""
    
    def load_area(self, area: str):
        """Load mock topology data."""
        from ..domain.models import BoundingBox, EdgeData, NodeData, TopologyData
        
        # Create minimal mock topology
        nodes = {
            "1": NodeData(x=-99.1500, y=19.4300, is_boundary=True),
            "2": NodeData(x=-99.1400, y=19.4300, is_boundary=False),
            "3": NodeData(x=-99.1400, y=19.4400, is_boundary=True),
        }
        
        edges = {
            ("1", "2", 0): EdgeData(length_m=100.0, speed_kph=50, n_cells=20, vmax_cells=3, geometry_points=[(-99.1500, 19.4300), (-99.1400, 19.4300)]),
            ("2", "3", 0): EdgeData(length_m=100.0, speed_kph=50, n_cells=20, vmax_cells=3, geometry_points=[(-99.1400, 19.4300), (-99.1400, 19.4400)]),
        }
        
        bbox = BoundingBox(min_x=-99.1500, max_x=-99.1400, min_y=19.4300, max_y=19.4400)
        
        return TopologyData(nodes=nodes, edges=edges, bbox=bbox)
    
    def load_bbox(self, bbox):
        """Load mock topology data for bounding box."""
        return self.load_area("mock_area")
"""
Simulation model interfaces and protocols.

Defines the Gymnasium-like interface for simulation models to enable
pluggable simulation engines (NaSch, ML agents, microsimulation, etc.).
"""

from typing import Protocol, Tuple, Dict, Optional, Any
from ..models import EdgeId, TopologyData, SimulationState, Metrics, SnapshotData


class SimulationModel(Protocol):
    """
    Gymnasium-like interface for traffic simulation models.
    
    This protocol defines the contract that simulation models must implement,
    enabling different simulation algorithms (NaSch, ML agents, microsimulation)
    to be used interchangeably.
    
    The interface follows Gymnasium conventions:
    - reset(): Initialize/restart the simulation
    - step(): Advance simulation by one time step
    - get_observation(): Get detailed state for visualization/analysis
    """
    
    def reset(self, topology: TopologyData, config: Optional[Dict[str, Any]] = None) -> SimulationState:
        """
        Reset simulation to initial state with new topology and configuration.
        
        Args:
            topology: Road network data for the simulation
            config: Optional simulation configuration parameters
            
        Returns:
            Initial simulation state after reset
            
        Note:
            This method should:
            1. Initialize cellular automata grid from topology
            2. Set up traffic lights at intersections
            3. Clear any existing vehicles
            4. Reset tick counter to 0
            5. Apply any configuration overrides
        """
        ...
    
    def step(self, actions: Optional[Dict[str, Any]] = None) -> Tuple[SimulationState, Metrics, bool]:
        """
        Advance simulation by one time step and return results.
        
        Args:
            actions: Optional actions/interventions to apply during step
                    (e.g., spawn vehicles, override traffic lights)
                    
        Returns:
            Tuple of (new_state, metrics, done) where:
            - new_state: Updated simulation state after step
            - metrics: Aggregated performance metrics
            - done: True if simulation should terminate
            
        Note:
            This method should:
            1. Apply NaSch rules synchronously to all vehicles
            2. Update traffic light states
            3. Handle boundary inflow/outflow
            4. Remove timed-out vehicles
            5. Calculate and return metrics
        """
        ...
    
    def get_observation(self) -> SnapshotData:
        """
        Get detailed simulation state for visualization and analysis.
        
        Returns:
            Complete snapshot data including vehicle positions, traffic light states,
            edge densities, and geographic information
            
        Note:
            This method provides more detailed information than the state returned
            by step(), optimized for rendering and detailed analysis rather than
            simulation control.
        """
        ...
    
    def get_state(self) -> SimulationState:
        """Get current compact simulation state."""
        ...
    
    def get_metrics(self) -> Metrics:
        """Get current aggregate simulation metrics."""
        ...

    def get_edge_states(self) -> Dict[EdgeId, Dict[str, Any]]:
        """Get per-edge snapshot state consumed by visualization payloads."""
        ...
    
    def get_current_tick(self) -> int:
        """Get current simulation time step."""
        ...
    
    def get_vehicle_count(self) -> int:
        """Get current number of active vehicles.""" 
        ...
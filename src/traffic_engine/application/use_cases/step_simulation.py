"""
StepSimulation use case implementation.

Advances the simulation by the requested number of ticks, handling vehicle
dynamics, traffic light updates, and metric collection.
"""

import logging
from typing import Optional, Dict, Any

from ..contracts import StepSimulationRequest, StepSimulationResponse
from ...domain.simulation import SimulationModel
from ...domain.models import Metrics

logger = logging.getLogger(__name__)


class StepSimulationUseCase:
    """
    Use case for advancing simulation time.
    
    Orchestrates the simulation stepping process:
    1. Validate step request parameters
    2. Apply any external actions
    3. Execute simulation steps
    4. Collect and return metrics
    """
    
    def __init__(self, simulation_model: SimulationModel):
        """
        Initialize use case with simulation model.
        
        Args:
            simulation_model: Active simulation model to step
        """
        self.simulation_model = simulation_model
    
    def execute(
        self, 
        simulation_id: str,
        request: StepSimulationRequest
    ) -> StepSimulationResponse:
        """
        Execute simulation step use case.
        
        Args:
            simulation_id: Identifier of simulation to step
            request: Step parameters
            
        Returns:
            Response with updated state and metrics
        """
        try:
            logger.info(f"Stepping simulation {simulation_id} for {request.n_ticks} ticks")
            
            # Apply any external actions if provided
            if request.actions:
                self._apply_actions(request.actions)
            
            # Execute simulation steps
            final_state = None
            final_metrics = None
            vehicles_spawned = 0
            vehicles_removed = 0
            initial_vehicles = 0
            initial_removed = 0
            
            for i in range(request.n_ticks):
                # Track initial vehicle count for first iteration
                if i == 0:
                    initial_vehicles = getattr(self.simulation_model, 'total_vehicles_spawned', 0)
                    initial_removed = getattr(self.simulation_model, 'total_vehicles_removed', 0)
                
                # Execute single simulation step
                state, metrics, done = self.simulation_model.step()
                final_state = state
                final_metrics = metrics
                
                # Stop if simulation completed
                if done:
                    logger.info(f"Simulation {simulation_id} completed at tick {state.tick}")
                    break
            
            # Calculate vehicle changes from simulation model tracking if available
            if hasattr(self.simulation_model, 'total_vehicles_spawned'):
                vehicles_spawned = self.simulation_model.total_vehicles_spawned - initial_vehicles
                vehicles_removed = self.simulation_model.total_vehicles_removed - initial_removed
            
            # Prepare response
            return StepSimulationResponse(
                simulation_id=simulation_id,
                new_tick=final_state.tick,
                metrics=self._metrics_to_dict(final_metrics),
                vehicles_spawned=vehicles_spawned,
                vehicles_removed=vehicles_removed,
                success=True
            )
            
        except ValueError as e:
            logger.warning(f"Validation error stepping simulation {simulation_id}: {e}")
            return StepSimulationResponse(
                simulation_id=simulation_id,
                new_tick=-1,
                metrics={},
                vehicles_spawned=0,
                vehicles_removed=0,
                success=False,
                error=f"Validation error: {str(e)}"
            )
            
        except Exception as e:
            logger.error(f"Unexpected error stepping simulation {simulation_id}: {e}")
            return StepSimulationResponse(
                simulation_id=simulation_id,
                new_tick=-1,
                metrics={},
                vehicles_spawned=0,
                vehicles_removed=0,
                success=False,
                error=f"Internal error: {str(e)}"
            )
    
    def _apply_actions(self, actions: Dict[str, Any]) -> None:
        """
        Apply external actions to simulation.
        
        Args:
            actions: Dictionary of actions to apply
            
        Note:
            Future extension point for external control (traffic light timing,
            route changes, incidents, etc.)
        """
        logger.debug(f"Applying actions: {actions}")
        
        # Traffic light actions
        if 'traffic_lights' in actions:
            traffic_light_actions = actions['traffic_lights']
            for light_id, light_config in traffic_light_actions.items():
                try:
                    self.simulation_model.update_traffic_light(light_id, light_config)
                    logger.debug(f"Updated traffic light {light_id}")
                except Exception as e:
                    logger.warning(f"Failed to update traffic light {light_id}: {e}")
        
        # Vehicle spawn actions
        if 'spawn_vehicles' in actions:
            spawn_config = actions['spawn_vehicles']
            try:
                count = spawn_config.get('count', 1)
                locations = spawn_config.get('locations', None)  # Specific spawn locations
                self.simulation_model.spawn_vehicles(count, locations)
                logger.debug(f"Spawned {count} vehicles")
            except Exception as e:
                logger.warning(f"Failed to spawn vehicles: {e}")
        
        # Incident actions (future: road closures, accidents)
        if 'incidents' in actions:
            incidents = actions['incidents']
            for incident in incidents:
                try:
                    self.simulation_model.apply_incident(incident)
                    logger.debug(f"Applied incident: {incident}")
                except Exception as e:
                    logger.warning(f"Failed to apply incident: {e}")
    
    def _metrics_to_dict(self, metrics: Metrics) -> Dict[str, Any]:
        """
        Convert Metrics object to dictionary for response.
        
        Args:
            metrics: Metrics object from simulation
            
        Returns:
            Dictionary representation of metrics using current Metrics fields
        """
        return {
            'tick': metrics.tick,
            'total_vehicles': metrics.total_vehicles,
            'avg_speed_kmh': metrics.avg_speed_kmh,
            'density': metrics.density,
            'throughput_veh_per_min': metrics.throughput_veh_per_min,
            'congestion_ratio': metrics.congestion_ratio,
            'boundary_inflow': metrics.boundary_inflow,
            'boundary_outflow': metrics.boundary_outflow,
        }
"""
GetSnapshot use case implementation.

Retrieves detailed simulation state snapshot for visualization and debugging,
including vehicle positions, traffic light states, and edge data.
"""

import logging
from typing import Any, Dict, List, Optional

from ..contracts import GetSnapshotRequest, GetSnapshotResponse
from ...domain.simulation import SimulationModel
from ...domain.models import VehicleType, SimulationState, LightState

logger = logging.getLogger(__name__)


class GetSnapshotUseCase:
    """
    Use case for retrieving detailed simulation snapshots.
    
    Provides comprehensive simulation state data suitable for:
    - Real-time visualization
    - Debugging and analysis
    - State persistence and replay
    """
    
    def __init__(self, simulation_model: SimulationModel):
        """
        Initialize use case with simulation model.
        
        Args:
            simulation_model: Active simulation model
        """
        self.simulation_model = simulation_model
    
    def execute(
        self, 
        simulation_id: str,
        request: GetSnapshotRequest
    ) -> GetSnapshotResponse:
        """
        Execute get snapshot use case.
        
        Args:
            simulation_id: Identifier of simulation
            request: Snapshot request parameters
            
        Returns:
            Response with detailed simulation snapshot
        """
        try:
            logger.info(f"Creating snapshot for simulation {simulation_id}")
            
            # Get simulation state
            state = self.simulation_model.get_state()
            
            # Build snapshot based on request parameters
            snapshot = {
                'meta': self._build_meta_info(state),
                'vehicles': self._build_vehicle_data(state, request),
                'traffic_lights': self._build_traffic_light_data(state),
            }
            
            # Add edge data if requested
            if request.include_edge_data:
                snapshot['edges'] = self._build_edge_data(state)
            
            logger.debug(f"Created snapshot for tick {state.tick} with {len(state.vehicles)} vehicles")
            
            return GetSnapshotResponse(
                simulation_id=simulation_id,
                snapshot=snapshot,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error creating snapshot for simulation {simulation_id}: {e}")
            return GetSnapshotResponse(
                simulation_id=simulation_id,
                snapshot={},
                success=False,
                error=f"Failed to create snapshot: {str(e)}"
            )
    
    def _build_meta_info(self, state: SimulationState) -> Dict[str, Any]:
        """
        Build metadata section of snapshot.
        
        Args:
            state: Current simulation state
            
        Returns:
            Metadata dictionary
        """
        return {
            'timestamp': self._get_timestamp(),
            'tick': state.tick,
            'total_vehicles': state.total_vehicles,
            'active_vehicles': state.active_vehicles,
            'simulation_time_s': state.tick,  # Assuming 1 tick = 1 second
            'real_time_ratio': getattr(state, 'real_time_ratio', 1.0),
            'topology_nodes': len(getattr(state, 'topology_nodes', {})),
            'topology_edges': len(getattr(state, 'topology_edges', {})),
            'traffic_lights_count': len(state.traffic_lights),
        }
    
    def _build_vehicle_data(
        self, 
        state: SimulationState,
        request: GetSnapshotRequest
    ) -> List[Dict[str, Any]]:
        """
        Build vehicle data section of snapshot.
        
        Args:
            state: Current simulation state
            request: Snapshot request parameters
            
        Returns:
            List of vehicle data dictionaries
        """
        vehicles_data = []
        
        # Apply vehicle type filter if specified
        type_filter = {
            value.value if hasattr(value, 'value') else str(value)
            for value in (request.vehicle_types_filter or [])
        }
        
        for vehicle in state.vehicles:
            # Apply type filter
            vehicle_type = vehicle.vtype.value if hasattr(vehicle.vtype, 'value') else str(vehicle.vtype)
            if type_filter and vehicle_type not in type_filter:
                continue
            
            vehicle_dict = {
                'id': vehicle.vid,
                'type': vehicle_type,
                'edge_id': vehicle.edge,
                'x': vehicle.x,
                'y': vehicle.y,
                'velocity': vehicle.velocity,
                'speed_kmh': vehicle.speed_kmh,
                'wait_ticks': vehicle.wait_ticks,
            }
            
            # Add detailed info if requested
            if request.include_vehicle_details:
                vehicle_dict.update({
                    'route': getattr(vehicle, 'route', []),
                    'route_position': getattr(vehicle, 'route_position', 0),
                    'spawn_tick': getattr(vehicle, 'spawn_tick', 0),
                    'timeout_counter': getattr(vehicle, 'timeout_counter', 0),
                    'total_distance': getattr(vehicle, 'total_distance', 0.0),
                    'avg_speed': getattr(vehicle, 'avg_speed', 0.0),
                    'stops_count': getattr(vehicle, 'stops_count', 0),
                    'is_leader': getattr(vehicle, 'is_leader', False),
                    'gap_ahead': getattr(vehicle, 'gap_ahead', 0),
                })
                
                # Add geographic position if available
                if hasattr(vehicle, 'geographic_position'):
                    vehicle_dict['geographic_position'] = vehicle.geographic_position
                else:
                    # Calculate from topology if possible
                    geo_pos = self._calculate_geographic_position(vehicle, state)
                    if geo_pos:
                        vehicle_dict['geographic_position'] = geo_pos
            
            vehicles_data.append(vehicle_dict)
        
        return vehicles_data
    
    def _build_traffic_light_data(self, state: SimulationState) -> List[Dict[str, Any]]:
        """
        Build traffic light data section of snapshot.
        
        Args:
            state: Current simulation state
            
        Returns:
            List of traffic light state dictionaries
        """
        lights_data = []
        
        for light_state in state.traffic_lights:
            light_dict = {
                'node_id': light_state.node_id,
                'phase': light_state.phase,
                'x': light_state.x,
                'y': light_state.y,
                'cycle_position': light_state.cycle_position,
                'time_to_change': light_state.time_to_change,
            }
            
            # Add configuration if available from simulation model
            try:
                light_config = self.simulation_model.get_traffic_light_config(light_state.node_id)
                if light_config:
                    light_dict.update({
                        'cycle_ticks': light_config.cycle_ticks,
                        'green_ratio': light_config.green_ratio,
                        'offset_ticks': light_config.offset_ticks,
                        'ns_edges_count': len(light_config.ns_edges),
                        'ew_edges_count': len(light_config.ew_edges),
                    })
            except Exception:
                pass  # Config not available
            
            lights_data.append(light_dict)
        
        return lights_data
    
    def _build_edge_data(self, state: SimulationState) -> Dict[str, Dict[str, Any]]:
        """
        Build edge data section of snapshot.
        
        Args:
            state: Current simulation state
            
        Returns:
            Dictionary mapping edge IDs to edge data
        """
        edges_data = {}
        
        # Get edge data from simulation model
        try:
            edge_states = self.simulation_model.get_edge_states()
            
            for edge_id, edge_state in edge_states.items():
                edge_dict = {
                    'vehicle_count': edge_state.get('vehicle_count', 0),
                    'density': edge_state.get('density', 0.0),
                    'average_speed': edge_state.get('average_speed', 0.0),
                    'flow': edge_state.get('flow', 0.0),
                    'occupancy_cells': edge_state.get('occupancy_cells', []),
                    'velocity_profile': edge_state.get('velocity_profile', []),
                }
                
                # Add physical properties if available
                if 'length_m' in edge_state:
                    edge_dict.update({
                        'length_m': edge_state['length_m'],
                        'n_cells': edge_state.get('n_cells', 0),
                        'max_speed_kph': edge_state.get('max_speed_kph', 0),
                    })
                
                edges_data[str(edge_id)] = edge_dict
                
        except Exception as e:
            logger.warning(f"Could not retrieve edge states: {e}")
            # Fallback: basic edge info
            for vehicle in state.vehicles:
                edge_id = str(vehicle.edge)
                if edge_id not in edges_data:
                    edges_data[edge_id] = {
                        'vehicle_count': 0,
                        'density': 0.0,
                        'average_speed': 0.0,
                        'flow': 0.0,
                    }
                edges_data[edge_id]['vehicle_count'] += 1
        
        return edges_data
    
    def _calculate_geographic_position(
        self, 
        vehicle: Any,
        state: SimulationState
    ) -> Optional[Dict[str, float]]:
        """
        Calculate geographic position for vehicle.
        
        Args:
            vehicle: Vehicle object
            state: Current simulation state
            
        Returns:
            Geographic position dictionary or None if not calculable
        """
        if hasattr(vehicle, 'x') and hasattr(vehicle, 'y'):
            return {'x': float(vehicle.x), 'y': float(vehicle.y)}

        get_edge_geometry = getattr(self.simulation_model, 'get_edge_geometry', None)
        if not callable(get_edge_geometry):
            return None

        if not hasattr(vehicle, 'edge') or not hasattr(vehicle, 'cell_pos'):
            return None

        try:
            edge_geo = get_edge_geometry(vehicle.edge)
            if edge_geo and len(edge_geo) >= 2:
                total_cells = len(edge_geo) - 1 if len(edge_geo) > 1 else 1
                progress = vehicle.cell_pos / total_cells if total_cells > 0 else 0

                if progress >= 1.0:
                    return {'x': edge_geo[-1][0], 'y': edge_geo[-1][1]}
                if progress <= 0.0:
                    return {'x': edge_geo[0][0], 'y': edge_geo[0][1]}

                x1, y1 = edge_geo[0]
                x2, y2 = edge_geo[-1]
                x = x1 + (x2 - x1) * progress
                y = y1 + (y2 - y1) * progress
                return {'x': x, 'y': y}
        except Exception:
            logger.debug("Could not calculate geographic position for vehicle %s", getattr(vehicle, 'vid', 'unknown'))
        
        return None
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for snapshot."""
        import datetime
        return datetime.datetime.now().isoformat()
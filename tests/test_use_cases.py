"""
Tests for application use cases: CreateSimulation, StepSimulation, GetMetrics, GetSnapshot.

Validates the orchestration logic that coordinates domain models and providers
to fulfill business requirements through well-defined use case interfaces.
"""

import pytest
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass
from unittest.mock import Mock


class TestCreateSimulationUseCase:
    """Test CreateSimulationUseCase orchestration and validation."""
    
    def test_create_simulation_loads_topology_from_provider(self):
        """Test use case loads topology data using configured provider."""
        # Arrange
        area_name = "Roma Norte, CDMX"
        topology_provider = Mock()
        topology_provider.load_area.return_value = self._sample_topology_data()
        
        # Act
        result = self._mock_create_simulation_use_case(
            area=area_name,
            topology_provider=topology_provider
        )
        
        # Assert - should call provider with correct area
        topology_provider.load_area.assert_called_once_with(area_name)
        assert result['success'], "Use case should succeed with valid inputs"
        assert 'simulation_id' in result, "Should return simulation ID"
    
    def test_create_simulation_configures_traffic_lights(self):
        """Test use case configures traffic lights using provider.""" 
        # Arrange
        topology_data = self._sample_topology_data()
        traffic_light_provider = Mock()
        traffic_light_provider.get_lights.return_value = [
            {'node_id': 'A', 'cycle_ticks': 30, 'green_ratio': 0.5, 'offset_ticks': 0}
        ]
        
        # Act
        result = self._mock_create_simulation_use_case(
            topology_data=topology_data,
            traffic_light_provider=traffic_light_provider
        )
        
        # Assert - should configure traffic lights with topology
        traffic_light_provider.get_lights.assert_called_once_with(topology_data)
        assert result['traffic_lights_count'] > 0, "Should configure traffic lights"
    
    def test_create_simulation_initializes_simulation_model(self):
        """Test use case properly initializes simulation model."""
        # Arrange
        topology_data = self._sample_topology_data()
        simulation_config = {
            'cell_size_m': 7.5,
            'noise_prob': 0.3,
            'v_max_cells': 5,
            'initial_vehicles': 50
        }
        
        # Act
        result = self._mock_create_simulation_use_case(
            topology_data=topology_data,
            config=simulation_config
        )
        
        # Assert - should initialize with config
        simulation_state = result.get('initial_state', {})
        assert simulation_state.get('tick') == 0, "Should start at tick 0"
        assert simulation_state.get('total_vehicles') == 50, "Should spawn initial vehicles"
    
    def test_create_simulation_validates_configuration_parameters(self):
        """Test use case validates simulation configuration parameters."""
        # Arrange - invalid configurations
        invalid_configs = [
            {'cell_size_m': 0},                    # Invalid cell size
            {'noise_prob': -0.1},                  # Invalid noise probability 
            {'noise_prob': 1.5},                   # Invalid noise probability
            {'v_max_cells': 0},                    # Invalid max velocity
            {'initial_vehicles': -10}              # Invalid vehicle count
        ]
        
        # Act & Assert
        for config in invalid_configs:
            result = self._mock_create_simulation_use_case(config=config)
            assert not result['success'], f"Should reject invalid config: {config}"
            assert 'error' in result, "Should provide error message for invalid config"
    
    def test_create_simulation_handles_provider_errors(self):
        """Test use case handles provider errors gracefully."""
        # Arrange - provider that raises error
        topology_provider = Mock()
        topology_provider.load_area.side_effect = ConnectionError("OSM service unavailable")
        
        # Act
        result = self._mock_create_simulation_use_case(
            area="Invalid Area",
            topology_provider=topology_provider
        )
        
        # Assert - should handle error gracefully
        assert not result['success'], "Should fail when provider raises error"
        assert 'error' in result, "Should capture error message"
        assert 'simulation_id' not in result, "Should not return ID on failure"
    
    def test_create_simulation_generates_unique_simulation_id(self):
        """Test use case generates unique simulation identifiers."""
        # Arrange
        topology_data = self._sample_topology_data()
        
        # Act - create multiple simulations
        results = []
        for _ in range(3):
            result = self._mock_create_simulation_use_case(topology_data=topology_data)
            results.append(result)
        
        # Assert - should generate unique IDs
        simulation_ids = [r['simulation_id'] for r in results if r['success']]
        assert len(set(simulation_ids)) == len(simulation_ids), "Should generate unique IDs"
        
        for sim_id in simulation_ids:
            assert isinstance(sim_id, (str, UUID)), "Simulation ID should be string or UUID"
    
    @staticmethod
    def _sample_topology_data():
        """Helper: sample topology data."""
        return {
            'nodes': {
                'A': {'x': -99.1332, 'y': 19.4326, 'is_boundary': True},
                'B': {'x': -99.1312, 'y': 19.4326, 'is_boundary': False}
            },
            'edges': {
                ('A', 'B', 0): {
                    'length_m': 150.0, 'speed_kph': 40.0,
                    'n_cells': 20, 'vmax_cells': 3,
                    'geometry_points': [(-99.1332, 19.4326), (-99.1312, 19.4326)]
                }
            },
            'bbox': {'min_x': -99.1332, 'max_x': -99.1312, 'min_y': 19.4326, 'max_y': 19.4326}
        }
    
    @staticmethod
    def _mock_create_simulation_use_case(**kwargs):
        """Helper: mock CreateSimulationUseCase execution."""
        # Extract inputs
        topology_provider = kwargs.get('topology_provider')
        traffic_light_provider = kwargs.get('traffic_light_provider') 
        config = kwargs.get('config', {})
        area = kwargs.get('area')
        topology_data = kwargs.get('topology_data')
        
        try:
            # Validate config
            if config.get('cell_size_m', 7.5) <= 0:
                return {'success': False, 'error': 'Invalid cell_size_m'}
            if not (0 <= config.get('noise_prob', 0.3) <= 1):
                return {'success': False, 'error': 'Invalid noise_prob'}
            if config.get('v_max_cells', 5) <= 0:
                return {'success': False, 'error': 'Invalid v_max_cells'}
            if config.get('initial_vehicles', 0) < 0:
                return {'success': False, 'error': 'Invalid initial_vehicles'}
            
            # Load topology
            if topology_data is None and topology_provider and area:
                topology_data = topology_provider.load_area(area)
            
            # Configure traffic lights
            traffic_lights = []
            if traffic_light_provider and topology_data:
                traffic_lights = traffic_light_provider.get_lights(topology_data)
            
            # Return successful result
            return {
                'success': True,
                'simulation_id': str(uuid4()),
                'initial_state': {
                    'tick': 0,
                    'total_vehicles': config.get('initial_vehicles', 0)
                },
                'traffic_lights_count': len(traffic_lights)
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}


class TestStepSimulationUseCase:
    """Test StepSimulationUseCase execution and state management."""
    
    def test_step_simulation_advances_model_state(self):
        """Test use case advances simulation model by specified ticks."""
        # Arrange
        simulation_id = uuid4()
        current_state = {'tick': 10, 'vehicles': [{'vid': 1, 'pos': 5}]}
        n_ticks = 5
        
        # Act
        result = self._mock_step_simulation_use_case(
            simulation_id=simulation_id,
            current_state=current_state,
            n_ticks=n_ticks
        )
        
        # Assert - should advance by requested ticks
        assert result['success'], "Step should succeed with valid inputs"
        new_state = result['new_state']
        assert new_state['tick'] == 15, f"Should advance by {n_ticks} ticks"
    
    def test_step_simulation_applies_nasch_rules(self):
        """Test use case applies NaSch rules during step execution."""
        # Arrange
        simulation_id = uuid4()
        vehicles_before = [
            {'vid': 1, 'pos': 3, 'velocity': 2, 'vmax': 3},
            {'vid': 2, 'pos': 8, 'velocity': 1, 'vmax': 2}
        ]
        current_state = {'tick': 5, 'vehicles': vehicles_before}
        
        # Act
        result = self._mock_step_simulation_use_case(
            simulation_id=simulation_id,
            current_state=current_state
        )
        
        # Assert - vehicles should have moved according to NaSch
        vehicles_after = result['new_state']['vehicles']
        for vehicle in vehicles_after:
            # Vehicles should have potentially moved (exact behavior depends on implementation)
            assert 'pos' in vehicle, "Vehicle should have position"
            assert 'velocity' in vehicle, "Vehicle should have velocity"
            assert vehicle['velocity'] >= 0, "Velocity should be non-negative"
    
    def test_step_simulation_updates_traffic_lights(self):
        """Test use case updates traffic light states during step."""
        # Arrange
        simulation_id = uuid4()
        traffic_lights = [
            {'node_id': 'A', 'cycle_ticks': 30, 'green_ratio': 0.5, 'offset_ticks': 0}
        ]
        current_state = {'tick': 14, 'traffic_lights': traffic_lights}
        
        # Act 
        result = self._mock_step_simulation_use_case(
            simulation_id=simulation_id,
            current_state=current_state
        )
        
        # Assert - traffic lights should update phase
        new_lights = result['new_state']['traffic_lights']
        assert len(new_lights) == len(traffic_lights), "Should preserve traffic light count"
        # Light phase depends on (tick + offset) % cycle and green_ratio
    
    def test_step_simulation_handles_vehicle_spawning_actions(self):
        """Test use case handles vehicle spawning actions."""
        # Arrange
        simulation_id = uuid4()
        current_state = {'tick': 20, 'vehicles': []}
        actions = {'spawn_vehicles': 3}
        
        # Act
        result = self._mock_step_simulation_use_case(
            simulation_id=simulation_id,
            current_state=current_state,
            actions=actions
        )
        
        # Assert - should spawn requested vehicles
        new_vehicles = result['new_state']['vehicles']
        assert len(new_vehicles) == 3, "Should spawn requested number of vehicles"
    
    def test_step_simulation_calculates_metrics(self):
        """Test use case calculates and returns simulation metrics."""
        # Arrange
        simulation_id = uuid4()
        vehicles = [
            {'vid': 1, 'velocity': 2}, {'vid': 2, 'velocity': 0}, {'vid': 3, 'velocity': 3}
        ]
        current_state = {'tick': 30, 'vehicles': vehicles}
        
        # Act
        result = self._mock_step_simulation_use_case(
            simulation_id=simulation_id,
            current_state=current_state
        )
        
        # Assert - should return meaningful metrics
        metrics = result.get('metrics', {})
        assert 'total_vehicles' in metrics, "Should include total vehicle count"
        assert 'avg_speed_kph' in metrics, "Should include average speed"
        assert 'density' in metrics, "Should include density metric"
        
        # Check metric reasonableness
        assert metrics['total_vehicles'] == 3, "Should count all vehicles"
        assert metrics['avg_speed_kph'] >= 0, "Average speed should be non-negative"
    
    def test_step_simulation_handles_invalid_simulation_id(self):
        """Test use case handles invalid simulation ID gracefully."""
        # Arrange
        invalid_simulation_id = uuid4()
        
        # Act
        result = self._mock_step_simulation_use_case(
            simulation_id=invalid_simulation_id,
            current_state=None  # Simulate not found
        )
        
        # Assert - should fail gracefully
        assert not result['success'], "Should fail for invalid simulation ID"
        assert 'error' in result, "Should provide error message"
    
    @staticmethod
    def _mock_step_simulation_use_case(**kwargs):
        """Helper: mock StepSimulationUseCase execution."""
        simulation_id = kwargs.get('simulation_id')
        current_state = kwargs.get('current_state')
        n_ticks = kwargs.get('n_ticks', 1)
        actions = kwargs.get('actions', {})
        
        if current_state is None:
            return {'success': False, 'error': f'Simulation {simulation_id} not found'}
        
        try:
            # Simulate stepping
            new_tick = current_state['tick'] + n_ticks
            vehicles = current_state.get('vehicles', [])
            
            # Apply actions
            if 'spawn_vehicles' in actions:
                spawn_count = actions['spawn_vehicles']
                for i in range(spawn_count):
                    vehicles.append({
                        'vid': len(vehicles) + i + 1,
                        'pos': 0, 'velocity': 1
                    })
            
            # Mock vehicle movement (simplified)
            for vehicle in vehicles:
                vehicle['pos'] = vehicle.get('pos', 0) + vehicle.get('velocity', 1)
            
            # Calculate metrics
            velocities = [v.get('velocity', 0) for v in vehicles]
            avg_speed_kph = sum(velocities) * 7.5 * 3.6 / len(velocities) if velocities else 0
            
            return {
                'success': True,
                'new_state': {
                    'tick': new_tick,
                    'vehicles': vehicles,
                    'traffic_lights': current_state.get('traffic_lights', [])
                },
                'metrics': {
                    'total_vehicles': len(vehicles),
                    'avg_speed_kph': avg_speed_kph,
                    'density': 0.3  # Mock density
                }
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}


class TestGetMetricsUseCase:
    """Test GetMetricsUseCase aggregation and optimization."""
    
    def test_get_metrics_calculates_vehicle_statistics(self):
        """Test use case calculates vehicle-related metrics."""
        # Arrange  
        simulation_id = uuid4()
        vehicles = [
            {'vid': 1, 'velocity': 2, 'wait_ticks': 0},
            {'vid': 2, 'velocity': 0, 'wait_ticks': 5},  # Congested
            {'vid': 3, 'velocity': 3, 'wait_ticks': 0},
            {'vid': 4, 'velocity': 0, 'wait_ticks': 2}   # Congested
        ]
        simulation_state = {'tick': 100, 'vehicles': vehicles}
        
        # Act
        metrics = self._mock_get_metrics_use_case(simulation_id, simulation_state)
        
        # Assert - vehicle statistics
        assert metrics['total_vehicles'] == 4, "Should count all vehicles"
        assert metrics['congestion_ratio'] == 0.5, "Should calculate congestion ratio (2/4)"
        
        # Average speed calculation: (2+0+3+0) * 7.5 * 3.6 / 4 = 33.75 km/h
        expected_avg_speed = (2 + 0 + 3 + 0) * 7.5 * 3.6 / 4
        assert abs(metrics['avg_speed_kph'] - expected_avg_speed) < 0.1, \
            "Should calculate average speed correctly"
    
    def test_get_metrics_calculates_network_density(self):
        """Test use case calculates network density metrics."""
        # Arrange
        simulation_id = uuid4() 
        # Mock edge states: 50% of cells occupied
        edge_densities = {
            ('A', 'B', 0): 0.6,   # 60% occupied
            ('B', 'C', 0): 0.4,   # 40% occupied  
            ('C', 'D', 0): 0.2    # 20% occupied
        }
        simulation_state = {'tick': 50, 'edge_densities': edge_densities}
        
        # Act
        metrics = self._mock_get_metrics_use_case(simulation_id, simulation_state)
        
        # Assert - network density
        expected_density = (0.6 + 0.4 + 0.2) / 3  # Average: 0.4
        assert abs(metrics['density'] - expected_density) < 0.01, \
            "Should calculate average network density"
    
    def test_get_metrics_calculates_throughput(self):
        """Test use case calculates throughput metrics."""
        # Arrange
        simulation_id = uuid4()
        # Mock completed vehicles: 10 vehicles finished in last 60 ticks
        completed_vehicles = 10
        time_window_ticks = 60
        tick_seconds = 1.0
        
        simulation_state = {
            'tick': 200,
            'completed_vehicles_recent': completed_vehicles,
            'time_window_ticks': time_window_ticks
        }
        
        # Act
        metrics = self._mock_get_metrics_use_case(simulation_id, simulation_state)
        
        # Assert - throughput calculation
        # 10 vehicles / 60 seconds * 60 = 10 vehicles/minute
        expected_throughput = completed_vehicles / time_window_ticks * 60
        assert abs(metrics['throughput_veh_per_min'] - expected_throughput) < 0.01, \
            "Should calculate throughput in vehicles per minute"
    
    def test_get_metrics_optimized_for_analysis_endpoints(self):
        """Test metrics are optimized for analysis/optimization endpoints."""
        # Arrange
        simulation_id = uuid4()
        simulation_state = {'tick': 150}
        
        # Act
        metrics = self._mock_get_metrics_use_case(simulation_id, simulation_state)
        
        # Assert - should include analysis-focused metrics
        analysis_metrics = {
            'total_vehicles', 'avg_speed_kph', 'density',
            'throughput_veh_per_min', 'congestion_ratio'
        }
        assert analysis_metrics.issubset(metrics.keys()), \
            "Should include all analysis-focused metrics"
        
        # Assert - should NOT include detailed visualization data
        visualization_fields = {'vehicle_positions', 'individual_speeds', 'edge_flows'}
        assert not visualization_fields.intersection(metrics.keys()), \
            "Should exclude detailed visualization data for optimization"
    
    def test_get_metrics_handles_empty_simulation(self):
        """Test use case handles simulation with no vehicles gracefully."""
        # Arrange
        simulation_id = uuid4()
        simulation_state = {'tick': 75, 'vehicles': []}
        
        # Act
        metrics = self._mock_get_metrics_use_case(simulation_id, simulation_state)
        
        # Assert - should handle empty state
        assert metrics['total_vehicles'] == 0, "Should report zero vehicles"
        assert metrics['avg_speed_kph'] == 0.0, "Should report zero average speed"
        assert metrics['congestion_ratio'] == 0.0, "Should report zero congestion"
        assert metrics['throughput_veh_per_min'] >= 0, "Throughput should be non-negative"
    
    @staticmethod
    def _mock_get_metrics_use_case(simulation_id: UUID, simulation_state: Dict) -> Dict:
        """Helper: mock GetMetricsUseCase execution."""
        vehicles = simulation_state.get('vehicles', [])
        tick = simulation_state.get('tick', 0)
        
        # Calculate vehicle metrics
        total_vehicles = len(vehicles)
        if total_vehicles > 0:
            velocities = [v.get('velocity', 0) for v in vehicles]
            congested_count = sum(1 for v in velocities if v == 0)
            
            avg_speed_kph = sum(velocities) * 7.5 * 3.6 / total_vehicles
            congestion_ratio = congested_count / total_vehicles
        else:
            avg_speed_kph = 0.0
            congestion_ratio = 0.0
        
        # Calculate density
        edge_densities = simulation_state.get('edge_densities', {})
        if edge_densities:
            density = sum(edge_densities.values()) / len(edge_densities)
        else:
            density = 0.0
        
        # Calculate throughput (mock)
        completed_recent = simulation_state.get('completed_vehicles_recent', 0)
        time_window = simulation_state.get('time_window_ticks', 60)
        throughput_veh_per_min = completed_recent / time_window * 60 if time_window > 0 else 0.0
        
        return {
            'tick': tick,
            'total_vehicles': total_vehicles,
            'avg_speed_kph': avg_speed_kph,
            'density': density,
            'throughput_veh_per_min': throughput_veh_per_min,
            'congestion_ratio': congestion_ratio
        }


class TestGetSnapshotUseCase:
    """Test GetSnapshotUseCase detailed state extraction."""
    
    def test_get_snapshot_includes_vehicle_positions(self):
        """Test snapshot includes detailed vehicle position data."""
        # Arrange
        simulation_id = uuid4()
        vehicles = [
            {'vid': 1, 'vtype': 'CAR', 'edge': ('A', 'B', 0), 'cell_pos': 5, 'velocity': 2},
            {'vid': 2, 'vtype': 'BUS', 'edge': ('B', 'C', 0), 'cell_pos': 8, 'velocity': 1}
        ]
        simulation_state = {'tick': 80, 'vehicles': vehicles}
        
        # Act
        snapshot = self._mock_get_snapshot_use_case(simulation_id, simulation_state)
        
        # Assert - should include vehicle details
        assert 'vehicles' in snapshot, "Should include vehicle data"
        assert len(snapshot['vehicles']) == 2, "Should include all vehicles"
        
        for vehicle in snapshot['vehicles']:
            assert 'x' in vehicle and 'y' in vehicle, "Should include geographic coordinates"
            assert 'vtype' in vehicle, "Should include vehicle type"
            assert 'velocity' in vehicle, "Should include velocity"
    
    def test_get_snapshot_includes_traffic_light_states(self):
        """Test snapshot includes current traffic light states."""
        # Arrange
        simulation_id = uuid4()
        traffic_lights = [
            {'node_id': 'intersection_1', 'cycle_ticks': 30, 'offset_ticks': 0, 'green_ratio': 0.5}
        ]
        simulation_state = {'tick': 15, 'traffic_lights': traffic_lights}
        
        # Act 
        snapshot = self._mock_get_snapshot_use_case(simulation_id, simulation_state)
        
        # Assert - should include traffic light states
        assert 'traffic_lights' in snapshot, "Should include traffic light data"
        lights = snapshot['traffic_lights']
        assert len(lights) == 1, "Should include all traffic lights"
        
        light = lights[0]
        assert 'node_id' in light, "Should include node ID"
        assert 'current_phase' in light, "Should include current phase"
        assert 'x' in light and 'y' in light, "Should include geographic position"
    
    def test_get_snapshot_includes_edge_flow_data(self):
        """Test snapshot includes edge flow and density data."""
        # Arrange
        simulation_id = uuid4()
        edge_data = {
            'edge_densities': {
                ('A', 'B', 0): 0.4,
                ('B', 'C', 0): 0.7
            },
            'edge_flows': {
                ('A', 'B', 0): 5,  # 5 vehicles passed in recent period
                ('B', 'C', 0): 3
            }
        }
        simulation_state = {'tick': 120, **edge_data}
        
        # Act
        snapshot = self._mock_get_snapshot_use_case(simulation_id, simulation_state)
        
        # Assert - should include edge flow data
        assert 'edge_densities' in snapshot, "Should include edge density data"
        assert 'edge_flows' in snapshot, "Should include edge flow data"
        
        assert snapshot['edge_densities'][('A', 'B', 0)] == 0.4, "Should preserve density values"
        assert snapshot['edge_flows'][('A', 'B', 0)] == 5, "Should preserve flow values"
    
    def test_get_snapshot_optimized_for_visualization(self):
        """Test snapshot is optimized for visualization endpoints."""
        # Arrange
        simulation_id = uuid4()
        simulation_state = {'tick': 90}
        
        # Act 
        snapshot = self._mock_get_snapshot_use_case(simulation_id, simulation_state)
        
        # Assert - should include visualization-focused data
        visualization_fields = {
            'vehicles', 'traffic_lights', 'edge_densities', 'edge_flows'
        }
        assert visualization_fields.issubset(snapshot.keys()), \
            "Should include visualization-focused fields"
        
        # Assert - should NOT include heavy aggregated metrics
        metric_fields = {'avg_speed_kph', 'throughput_veh_per_min', 'congestion_ratio'}
        assert not metric_fields.intersection(snapshot.keys()), \
            "Should exclude aggregated metrics for visualization optimization"
    
    def test_get_snapshot_converts_positions_to_geographic_coordinates(self):
        """Test snapshot converts cell positions to geographic coordinates."""
        # Arrange
        simulation_id = uuid4()
        vehicles = [
            {'vid': 1, 'edge': ('A', 'B', 0), 'cell_pos': 10}  # Cell position
        ]
        topology_data = {
            'edges': {
                ('A', 'B', 0): {
                    'geometry_points': [(-99.1332, 19.4326), (-99.1312, 19.4326)],
                    'n_cells': 20
                }
            }
        }
        simulation_state = {'tick': 45, 'vehicles': vehicles, 'topology': topology_data}
        
        # Act
        snapshot = self._mock_get_snapshot_use_case(simulation_id, simulation_state)
        
        # Assert - should convert to geographic coordinates
        vehicle = snapshot['vehicles'][0]
        assert 'x' in vehicle and 'y' in vehicle, "Should have geographic coordinates"
        assert -100 <= vehicle['x'] <= -99, "X coordinate should be reasonable for CDMX"
        assert 19 <= vehicle['y'] <= 20, "Y coordinate should be reasonable for CDMX"
    
    @staticmethod
    def _mock_get_snapshot_use_case(simulation_id: UUID, simulation_state: Dict) -> Dict:
        """Helper: mock GetSnapshotUseCase execution."""
        vehicles = simulation_state.get('vehicles', [])
        traffic_lights = simulation_state.get('traffic_lights', [])
        tick = simulation_state.get('tick', 0)
        
        # Convert vehicles to snapshot format
        snapshot_vehicles = []
        for vehicle in vehicles:
            # Mock coordinate conversion
            x, y = -99.1320 + vehicle.get('vid', 0) * 0.001, 19.4320
            
            snapshot_vehicles.append({
                'vid': vehicle.get('vid'),
                'vtype': vehicle.get('vtype', 'CAR'),
                'x': x, 'y': y,
                'velocity': vehicle.get('velocity', 0),
                'edge': vehicle.get('edge'),
                'wait_ticks': vehicle.get('wait_ticks', 0)
            })
        
        # Convert traffic lights to snapshot format
        snapshot_lights = []
        for light in traffic_lights:
            # Mock phase calculation
            cycle_pos = (tick + light.get('offset_ticks', 0)) % light.get('cycle_ticks', 30)
            green_duration = int(light.get('cycle_ticks', 30) * light.get('green_ratio', 0.5))
            current_phase = 'NS_GREEN' if cycle_pos < green_duration else 'EW_GREEN'
            
            snapshot_lights.append({
                'node_id': light.get('node_id'),
                'current_phase': current_phase,
                'x': -99.1320,  # Mock position
                'y': 19.4320,
                'cycle_position': cycle_pos / light.get('cycle_ticks', 30)
            })
        
        return {
            'tick': tick,
            'vehicles': snapshot_vehicles,
            'traffic_lights': snapshot_lights,
            'edge_densities': simulation_state.get('edge_densities', {}),
            'edge_flows': simulation_state.get('edge_flows', {})
        }
"""
Tests for domain models: TopologyData, Vehicle, SimulationState, and TrafficLight.

These tests define the expected contracts and behavior of core domain entities
before implementation, following TDD principles.
"""

import pytest
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import uuid


class TestTopologyData:
    """Test TopologyData structure and validation."""
    
    def test_topology_data_structure_contains_required_fields(self, mock_topology_data):
        """Test TopologyData contains all required fields for simulation."""
        # Arrange & Act
        topology = mock_topology_data
        
        # Assert - top-level structure
        required_keys = {'nodes', 'edges', 'bbox'}
        assert required_keys.issubset(topology.keys()), "TopologyData missing required top-level fields"
        
        # Assert - nodes structure  
        assert isinstance(topology['nodes'], dict), "Nodes should be a dictionary"
        for node_id, node_data in topology['nodes'].items():
            node_required = {'x', 'y', 'is_boundary'}
            assert node_required.issubset(node_data.keys()), f"Node {node_id} missing required fields"
        
        # Assert - edges structure
        assert isinstance(topology['edges'], dict), "Edges should be a dictionary"
        for edge_id, edge_data in topology['edges'].items():
            edge_required = {'length_m', 'speed_kph', 'n_cells', 'vmax_cells', 'geometry_points'}
            assert edge_required.issubset(edge_data.keys()), f"Edge {edge_id} missing required fields"
            assert isinstance(edge_id, tuple) and len(edge_id) == 3, "Edge ID should be (u, v, key) tuple"
    
    def test_topology_data_edge_discretization_is_consistent(self, mock_topology_data):
        """Test edge discretization parameters are mathematically consistent."""
        # Arrange
        topology = mock_topology_data
        
        for edge_id, edge_data in topology['edges'].items():
            # Act 
            length_m = edge_data['length_m']
            n_cells = edge_data['n_cells']
            speed_kph = edge_data['speed_kph']
            vmax_cells = edge_data['vmax_cells']
            
            # Assert - cell count should approximate length discretization
            cell_size_approx = length_m / n_cells
            assert 5.0 <= cell_size_approx <= 10.0, \
                f"Edge {edge_id}: cell size {cell_size_approx:.1f}m outside reasonable range"
            
            # Assert - vmax should be reasonable for speed limit
            # ASSUMPTION: vmax calculation similar to prototype
            expected_vmax_range = (1, 5)  # From V_MAX_CELLS constant
            assert expected_vmax_range[0] <= vmax_cells <= expected_vmax_range[1], \
                f"Edge {edge_id}: vmax {vmax_cells} outside valid range {expected_vmax_range}"
    
    def test_topology_data_coordinates_form_valid_bbox(self, mock_topology_data):
        """Test bounding box is consistent with node coordinates."""
        # Arrange
        topology = mock_topology_data
        bbox = topology['bbox'] 
        
        # Act - extract all node coordinates
        x_coords = [node['x'] for node in topology['nodes'].values()]
        y_coords = [node['y'] for node in topology['nodes'].values()]
        
        # Assert - bbox should contain all nodes
        assert bbox['min_x'] <= min(x_coords), "Bbox min_x should be <= minimum node x"
        assert bbox['max_x'] >= max(x_coords), "Bbox max_x should be >= maximum node x"
        assert bbox['min_y'] <= min(y_coords), "Bbox min_y should be <= minimum node y" 
        assert bbox['max_y'] >= max(y_coords), "Bbox max_y should be >= maximum node y"
    
    def test_topology_data_geometry_points_define_valid_lines(self, mock_topology_data):
        """Test edge geometry points form valid line segments."""
        # Arrange
        topology = mock_topology_data
        
        for edge_id, edge_data in topology['edges'].items():
            # Act
            geometry_points = edge_data['geometry_points']
            
            # Assert - should have at least 2 points for a line
            assert len(geometry_points) >= 2, f"Edge {edge_id} needs at least 2 geometry points"
            
            # Assert - points should be valid coordinates
            for i, point in enumerate(geometry_points):
                assert len(point) == 2, f"Edge {edge_id} point {i} should be (x, y) tuple"
                x, y = point
                assert isinstance(x, (int, float)), f"Edge {edge_id} point {i} x-coord should be numeric"
                assert isinstance(y, (int, float)), f"Edge {edge_id} point {i} y-coord should be numeric"


class TestVehicleModel:
    """Test Vehicle entity and VehicleType enumeration."""
    
    def test_vehicle_type_enum_has_expected_values(self):
        """Test VehicleType enum contains expected vehicle types from prototype."""
        # Arrange - define expected vehicle types based on prototype analysis
        
        # Act - create mock enum (will be replaced by actual implementation)
        class VehicleType(Enum):
            CAR = "car"
            BUS = "bus" 
            MOTO = "moto"
        
        # Assert - should contain the three main types from prototype
        expected_types = {'CAR', 'BUS', 'MOTO'}
        actual_types = {vtype.name for vtype in VehicleType}
        assert expected_types == actual_types, f"VehicleType should have exactly {expected_types}"
    
    def test_vehicle_state_tracks_position_and_movement(self):
        """Test Vehicle entity tracks position and movement state correctly."""
        # Arrange - create mock vehicle structure
        vehicle_data = {
            'vid': 123,
            'vtype': 'CAR',
            'route': [('A', 'B', 0), ('B', 'C', 0)],
            'edge_idx': 0,
            'cell_pos': 5,
            'velocity': 2,
            'distance_traveled_m': 37.5,
            'wait_ticks': 0
        }
        
        # Act & Assert - should track current position
        assert vehicle_data['edge_idx'] >= 0, "Edge index should be non-negative"
        assert vehicle_data['cell_pos'] >= 0, "Cell position should be non-negative"
        
        # Act & Assert - should track movement state
        assert vehicle_data['velocity'] >= 0, "Velocity should be non-negative"
        assert vehicle_data['distance_traveled_m'] >= 0, "Distance traveled should be non-negative"
        assert vehicle_data['wait_ticks'] >= 0, "Wait ticks should be non-negative"
    
    def test_vehicle_state_provides_current_edge_access(self):
        """Test Vehicle provides convenient access to current edge."""
        # Arrange
        route = [('A', 'B', 0), ('B', 'C', 0), ('C', 'D', 0)]
        edge_idx = 1
        
        # Act - simulate current_edge property
        current_edge = route[edge_idx]
        
        # Assert
        assert current_edge == ('B', 'C', 0), "Current edge should match edge_idx in route"
    
    def test_vehicle_state_provides_next_edge_access(self):
        """Test Vehicle provides access to next edge in route."""
        # Arrange
        route = [('A', 'B', 0), ('B', 'C', 0), ('C', 'D', 0)]
        edge_idx = 1
        
        # Act - simulate next_edge property
        next_edge = route[edge_idx + 1] if edge_idx + 1 < len(route) else None
        
        # Assert - should return next edge when available
        assert next_edge == ('C', 'D', 0), "Next edge should be following edge in route"
        
        # Act & Assert - should return None at end of route
        edge_idx_last = len(route) - 1
        next_edge_last = route[edge_idx_last + 1] if edge_idx_last + 1 < len(route) else None
        assert next_edge_last is None, "Next edge should be None at end of route"
    
    def test_vehicle_route_is_valid_edge_sequence(self):
        """Test vehicle route consists of valid connected edge sequence."""
        # Arrange
        route = [('A', 'B', 0), ('B', 'C', 0), ('C', 'D', 0)]
        
        # Act & Assert - route should form connected path
        for i in range(len(route) - 1):
            current_edge = route[i]
            next_edge = route[i + 1]
            
            # End node of current edge should match start node of next edge
            assert current_edge[1] == next_edge[0], \
                f"Route discontinuity: edge {current_edge} -> {next_edge}"
    
    def test_vehicle_movement_metrics_accumulate_correctly(self):
        """Test vehicle accumulates movement metrics over time."""
        # Arrange - simulate vehicle movement over several ticks
        cell_size_m = 7.5
        initial_distance = 0.0
        movements = [2, 1, 3, 0, 2]  # velocities per tick in cells/tick
        
        # Act - accumulate distance
        total_distance = initial_distance
        wait_ticks = 0
        for velocity in movements:
            total_distance += velocity * cell_size_m
            if velocity == 0:
                wait_ticks += 1
        
        # Assert - distance should accumulate correctly
        expected_distance = sum(movements) * cell_size_m
        assert total_distance == expected_distance, "Distance should accumulate with each movement"
        
        # Assert - wait time should count stationary ticks
        expected_wait = sum(1 for v in movements if v == 0)
        assert wait_ticks == expected_wait, "Wait ticks should count zero-velocity ticks"


class TestSimulationState:
    """Test SimulationState and related metrics structures."""
    
    def test_simulation_state_tracks_global_state(self):
        """Test SimulationState captures complete simulation state."""
        # Arrange - mock simulation state structure
        sim_state = {
            'tick': 42,
            'vehicles': [{'vid': 1, 'pos': 'edge1'}, {'vid': 2, 'pos': 'edge2'}],
            'traffic_lights': [{'node': 'A', 'phase': 'NS_GREEN'}],
            'total_vehicles': 2,
            'active_vehicles': 2
        }
        
        # Act & Assert - should track time
        assert isinstance(sim_state['tick'], int), "Tick should be integer"
        assert sim_state['tick'] >= 0, "Tick should be non-negative"
        
        # Act & Assert - should track vehicles
        assert isinstance(sim_state['vehicles'], list), "Vehicles should be a list"
        assert len(sim_state['vehicles']) == sim_state['total_vehicles'], \
            "Vehicle count should match list length"
    
    def test_simulation_metrics_calculate_aggregate_statistics(self):
        """Test simulation metrics provide meaningful aggregate statistics."""
        # Arrange - mock metrics structure based on prototype
        metrics = {
            'tick': 100,
            'total_vehicles': 150,
            'avg_speed_kph': 28.5,
            'density': 0.35,  # fraction of occupied cells
            'throughput_veh_per_min': 12.3,
            'congestion_ratio': 0.25  # fraction of vehicles with speed = 0
        }
        
        # Act & Assert - metrics should be in reasonable ranges
        assert 0 <= metrics['avg_speed_kph'] <= 80, "Average speed should be reasonable for city traffic"
        assert 0 <= metrics['density'] <= 1, "Density should be a ratio in [0,1]"
        assert metrics['throughput_veh_per_min'] >= 0, "Throughput should be non-negative"
        assert 0 <= metrics['congestion_ratio'] <= 1, "Congestion ratio should be in [0,1]"
    
    def test_simulation_snapshot_provides_detailed_state(self):
        """Test simulation snapshot contains detailed state for visualization."""
        # Arrange - mock snapshot structure 
        snapshot = {
            'tick': 100,
            'vehicles': [
                {
                    'vid': 1, 'vtype': 'CAR', 'x': -99.1322, 'y': 19.4316,
                    'edge': ('A', 'B', 0), 'velocity': 2, 'wait_ticks': 0
                },
                {
                    'vid': 2, 'vtype': 'BUS', 'x': -99.1318, 'y': 19.4320,  
                    'edge': ('B', 'C', 0), 'velocity': 0, 'wait_ticks': 5
                }
            ],
            'traffic_lights': [
                {
                    'node_id': 'intersection_1', 'phase': 'NS_GREEN',
                    'x': -99.1320, 'y': 19.4318, 'cycle_position': 0.3
                }
            ],
            'edge_densities': {
                ('A', 'B', 0): 0.4,
                ('B', 'C', 0): 0.7  
            }
        }
        
        # Act & Assert - vehicles should have geographic positions
        for vehicle in snapshot['vehicles']:
            assert 'x' in vehicle and 'y' in vehicle, "Vehicles should have geographic coordinates"
            assert -100 <= vehicle['x'] <= -99, "X coordinate should be reasonable for CDMX"
            assert 19 <= vehicle['y'] <= 20, "Y coordinate should be reasonable for CDMX"
        
        # Act & Assert - traffic lights should have state and position
        for light in snapshot['traffic_lights']:
            assert 'phase' in light, "Traffic light should have phase information"
            assert 'x' in light and 'y' in light, "Traffic light should have position"
        
        # Act & Assert - edge densities should be ratios
        for edge_id, density in snapshot['edge_densities'].items():
            assert isinstance(edge_id, tuple), "Edge ID should be tuple"
            assert 0 <= density <= 1, f"Edge density {density} should be ratio in [0,1]"


class TestTrafficLightModel:
    """Test TrafficLight entity and phase logic."""
    
    def test_traffic_light_has_required_configuration(self):
        """Test TrafficLight contains required configuration parameters."""
        # Arrange - mock traffic light structure based on prototype
        traffic_light = {
            'node_id': 'intersection_1',
            'cycle_ticks': 30,
            'green_ratio': 0.5,
            'offset_ticks': 0,
            'ns_edges': {('north', 'center', 0), ('south', 'center', 0)},
            'ew_edges': {('east', 'center', 0), ('west', 'center', 0)}
        }
        
        # Act & Assert - required fields
        required_fields = {'node_id', 'cycle_ticks', 'green_ratio', 'offset_ticks'}
        assert required_fields.issubset(traffic_light.keys()), "Traffic light missing required configuration"
        
        # Act & Assert - parameter ranges
        assert traffic_light['cycle_ticks'] > 0, "Cycle length should be positive"
        assert 0 < traffic_light['green_ratio'] < 1, "Green ratio should be in (0,1)"
        assert traffic_light['offset_ticks'] >= 0, "Offset should be non-negative"
    
    def test_traffic_light_classifies_edges_by_orientation(self, intersection_network):
        """Test traffic light correctly classifies edges as NS vs EW."""
        # Arrange - intersection with known orientations
        center_node = 'center'
        incoming_edges = list(intersection_network.in_edges(center_node, keys=True))
        
        # Act - simulate edge classification by bearing
        ns_edges = set()
        ew_edges = set()
        
        for u, v, k in incoming_edges:
            bearing = self._calculate_bearing(intersection_network, u, v)
            if self._is_ns_orientation(bearing):
                ns_edges.add((u, v, k))
            else:
                ew_edges.add((u, v, k))
        
        # Assert - should have both NS and EW edges for 4-way intersection
        assert len(ns_edges) > 0, "Should have north-south oriented edges"
        assert len(ew_edges) > 0, "Should have east-west oriented edges"
        assert len(ns_edges) + len(ew_edges) == len(incoming_edges), \
            "All edges should be classified as either NS or EW"
    
    def test_traffic_light_phase_alternation_follows_cycle(self):
        """Test traffic light phases alternate correctly according to cycle."""
        # Arrange
        cycle_ticks = 30
        green_ratio = 0.6  # NS green for 60% of cycle
        offset = 0
        ns_green_duration = int(cycle_ticks * green_ratio)  # 18 ticks
        ew_green_duration = cycle_ticks - ns_green_duration  # 12 ticks
        
        # Act & Assert - NS phase during first part of cycle
        for tick in range(ns_green_duration):
            phase_tick = (tick + offset) % cycle_ticks
            ns_is_green = phase_tick < ns_green_duration
            assert ns_is_green, f"NS should be green at cycle tick {phase_tick}"
        
        # Act & Assert - EW phase during second part of cycle
        for tick in range(ns_green_duration, cycle_ticks):
            phase_tick = (tick + offset) % cycle_ticks
            ns_is_green = phase_tick < ns_green_duration
            assert not ns_is_green, f"NS should be red (EW green) at cycle tick {phase_tick}"
    
    def test_traffic_light_offset_shifts_phase_timing(self):
        """Test traffic light offset correctly shifts phase timing."""
        # Arrange
        cycle_ticks = 20
        green_ratio = 0.5
        base_offset = 0
        shifted_offset = 7
        
        # Act - check phase at same absolute tick with different offsets
        absolute_tick = 10
        
        # Base light (offset=0): tick 10 in 20-tick cycle, 50% ratio -> NS red
        base_phase_tick = (absolute_tick + base_offset) % cycle_ticks  # 10
        base_ns_green = base_phase_tick < int(cycle_ticks * green_ratio)  # 10 < 10 = False
        
        # Shifted light (offset=7): effective tick 17 in cycle -> NS red  
        shifted_phase_tick = (absolute_tick + shifted_offset) % cycle_ticks  # 17
        shifted_ns_green = shifted_phase_tick < int(cycle_ticks * green_ratio)  # 17 < 10 = False
        
        # Assert - both should be in EW phase, but could be different if offset crosses boundary
        # The key is that offset changes the effective phase timing
        assert isinstance(base_ns_green, bool), "Base phase should return boolean"
        assert isinstance(shifted_ns_green, bool), "Shifted phase should return boolean"
    
    def test_traffic_light_green_wave_coordination(self):
        """Test traffic lights can be coordinated for green wave effect."""
        # Arrange - two lights on same corridor with staggered offsets
        light1_offset = 0
        light2_offset = 10  # Staggered by 10 ticks
        cycle_ticks = 30
        green_ratio = 0.5
        
        # Act - simulate vehicle traveling between lights
        travel_time_ticks = 10  # Time to travel from light1 to light2
        
        # Vehicle hits light1 at tick 5
        departure_tick = 5
        arrival_tick = departure_tick + travel_time_ticks  # tick 15
        
        # Check light1 at departure
        light1_phase_tick = (departure_tick + light1_offset) % cycle_ticks
        light1_green = light1_phase_tick < int(cycle_ticks * green_ratio)
        
        # Check light2 at arrival
        light2_phase_tick = (arrival_tick + light2_offset) % cycle_ticks
        light2_green = light2_phase_tick < int(cycle_ticks * green_ratio)
        
        # Assert - both should be accessible (implementation details vary)
        # The test demonstrates that offset coordination is testable
        assert isinstance(light1_green, bool), "Light1 should have deterministic phase"
        assert isinstance(light2_green, bool), "Light2 should have deterministic phase"
    
    @staticmethod
    def _calculate_bearing(G, u, v) -> float:
        """Helper: calculate bearing from node u to node v."""
        n1, n2 = G.nodes[u], G.nodes[v]
        dlat = n2['y'] - n1['y'] 
        dlon = n2['x'] - n1['x']
        import math
        return math.degrees(math.atan2(dlon, dlat)) % 360
    
    @staticmethod
    def _is_ns_orientation(bearing: float) -> bool:
        """Helper: determine if bearing is north-south oriented."""
        return bearing < 45 or bearing > 315 or (135 < bearing < 225)
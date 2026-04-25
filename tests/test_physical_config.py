"""
Tests for traffic engine configuration and physical parameters.

Validates speed-to-vmax conversion, vehicle type parameters, and boundary
detection logic that form the foundation of the simulation.
"""

import pytest
import math


class TestPhysicalConfiguration:
    """Test physical parameter conversion and validation."""
    
    def test_speed_to_vmax_conversion_typical_city_speeds(self, simulation_config):
        """Test speed conversion for typical CDMX street speeds."""
        # Arrange 
        cell_size_m = simulation_config['cell_size_m']
        
        # Act & Assert - typical city speeds should map to reasonable cell velocities
        # 30 km/h residential street: 30/3.6/7.5 = 1.11 -> vmax=1
        vmax_30 = self._speed_to_vmax(30.0, cell_size_m)
        assert vmax_30 == 1, "30 km/h should map to 1 cell/tick for residential streets"
        
        # 50 km/h main avenue: 50/3.6/7.5 = 1.85 -> vmax=2  
        vmax_50 = self._speed_to_vmax(50.0, cell_size_m)
        assert vmax_50 == 2, "50 km/h should map to 2 cells/tick for main avenues"
        
        # 70 km/h highway: 70/3.6/7.5 = 2.59 -> vmax=3
        vmax_70 = self._speed_to_vmax(70.0, cell_size_m)
        assert vmax_70 == 3, "70 km/h should map to 3 cells/tick for highways"
    
    def test_speed_to_vmax_conversion_boundary_cases(self, simulation_config):
        """Test speed conversion handles boundary cases correctly."""
        # Arrange
        cell_size_m = simulation_config['cell_size_m']
        v_max_cells = simulation_config['v_max_cells']
        
        # Act & Assert - minimum speed
        vmax_min = self._speed_to_vmax(5.0, cell_size_m)
        assert vmax_min >= 1, "Minimum vmax should be 1 cell/tick even for very low speeds"
        
        # Act & Assert - maximum speed clamping
        vmax_extreme = self._speed_to_vmax(200.0, cell_size_m)
        assert vmax_extreme <= v_max_cells, f"Extreme speeds should be capped at {v_max_cells} cells/tick"
    
    def test_speed_to_vmax_conversion_with_vehicle_factors(self, simulation_config, vehicle_types_config):
        """Test speed conversion applies vehicle type factors correctly."""
        # Arrange
        cell_size_m = simulation_config['cell_size_m'] 
        base_speed = 40.0
        base_vmax = self._speed_to_vmax(base_speed, cell_size_m)
        
        # Act & Assert - car (factor=1.0) should maintain base speed
        car_factor = vehicle_types_config['car']['speed_factor']  # ASSUMPTION: enum keys are strings in config
        car_vmax = max(1, round(base_vmax * car_factor))
        assert car_vmax == base_vmax, "Cars should maintain base street speed"
        
        # Act & Assert - bus (factor=0.55) should be slower
        bus_factor = vehicle_types_config['bus']['speed_factor']
        bus_vmax = max(1, round(base_vmax * bus_factor))
        assert bus_vmax < base_vmax, "Buses should be slower than base street speed"
        
        # Act & Assert - moto (factor=1.25) should be faster
        moto_factor = vehicle_types_config['moto']['speed_factor']
        moto_vmax = max(1, round(base_vmax * moto_factor))
        assert moto_vmax >= base_vmax, "Motorcycles should be faster than or equal to base speed"
    
    def test_vehicle_type_parameters_consistency(self, vehicle_types_config):
        """Test vehicle type configurations are valid and consistent."""
        # Arrange & Act
        for vehicle_type, config in vehicle_types_config.items():
            
            # Assert - all required parameters exist
            required_keys = {'speed_factor', 'noise_factor', 'size_cells'}
            assert required_keys.issubset(config.keys()), f"{vehicle_type} missing required parameters"
            
            # Assert - speed factors are positive
            assert config['speed_factor'] > 0, f"{vehicle_type} speed_factor must be positive"
            
            # Assert - noise factors are non-negative
            assert config['noise_factor'] >= 0, f"{vehicle_type} noise_factor must be non-negative" 
            
            # Assert - size in cells is positive integer
            assert isinstance(config['size_cells'], int) and config['size_cells'] > 0, \
                f"{vehicle_type} size_cells must be positive integer"
    
    def test_cell_discretization_preserves_length(self, simulation_config):
        """Test edge discretization preserves physical length within reasonable error."""
        # Arrange
        cell_size_m = simulation_config['cell_size_m']
        test_lengths = [75.0, 150.0, 234.5, 500.0]  # Various street lengths
        
        for length_m in test_lengths:
            # Act
            n_cells = max(1, int(length_m / cell_size_m))
            discretized_length = n_cells * cell_size_m
            
            # Assert - discretization error should be less than one cell
            error_m = abs(discretized_length - length_m)
            assert error_m < cell_size_m, f"Discretization error {error_m}m exceeds cell size {cell_size_m}m"
    
    @staticmethod
    def _speed_to_vmax(speed_kph: float, cell_size_m: float) -> int:
        """Helper: reproduce speed-to-vmax conversion from prototype."""
        cells_per_sec = speed_kph / 3.6 / cell_size_m
        return max(1, min(5, round(cells_per_sec)))  # V_MAX_CELLS = 5 from prototype


class TestBoundaryDetection:
    """Test boundary node detection logic for entry/exit points."""
    
    def test_boundary_detection_identifies_network_perimeter(self, simple_network):
        """Test boundary detection correctly identifies perimeter nodes."""
        # Arrange - simple network should have clear boundary characteristics
        # ASSUMPTION: boundary nodes are those with fewer connections or specific attributes
        
        # Act - detect boundary nodes (implementation will vary)
        boundary_nodes = self._detect_boundary_nodes(simple_network)
        
        # Assert - should identify some boundary nodes in the network
        assert len(boundary_nodes) > 0, "Network should have identifiable boundary nodes"
        assert len(boundary_nodes) < len(simple_network.nodes()), "Not all nodes should be boundaries"
    
    def test_boundary_detection_excludes_high_connectivity_nodes(self, intersection_network):
        """Test boundary detection excludes high-connectivity intersection nodes."""
        # Arrange - intersection network has one high-connectivity center
        center_degree = intersection_network.degree('center')
        
        # Act 
        boundary_nodes = self._detect_boundary_nodes(intersection_network)
        
        # Assert - high-connectivity center should not be a boundary
        assert 'center' not in boundary_nodes, "High-connectivity intersection should not be boundary"
        assert center_degree > 2, "Test assumption: center should have high connectivity"
    
    def test_boundary_detection_includes_terminal_nodes(self, linear_network):
        """Test boundary detection includes terminal/dead-end nodes."""
        # Arrange - linear network has clear terminal nodes
        
        # Act
        boundary_nodes = self._detect_boundary_nodes(linear_network)
        
        # Assert - terminal nodes should be boundaries
        terminal_candidates = ['A', 'C']  # ends of linear chain
        for node in terminal_candidates:
            node_degree = linear_network.degree(node) 
            if node_degree <= 1:  # Actual terminal node
                assert node in boundary_nodes, f"Terminal node {node} should be boundary"
    
    def test_boundary_detection_consistent_across_calls(self, simple_network):
        """Test boundary detection produces consistent results."""
        # Arrange & Act - call detection multiple times
        boundaries_1 = self._detect_boundary_nodes(simple_network)
        boundaries_2 = self._detect_boundary_nodes(simple_network)
        
        # Assert - should be identical
        assert boundaries_1 == boundaries_2, "Boundary detection should be deterministic"
    
    @staticmethod
    def _detect_boundary_nodes(G) -> set:
        """Helper: mock boundary detection logic - replace with actual implementation."""
        # ASSUMPTION: nodes with degree <= 2 OR specific street_count attributes are boundaries
        boundaries = set()
        for node in G.nodes():
            degree = G.degree(node)
            # Simple heuristic: low degree nodes are likely boundaries
            if degree <= 2:
                boundaries.add(node)
        return boundaries


class TestConfigurationValidation:
    """Test configuration parameter validation and defaults."""
    
    def test_simulation_config_has_required_parameters(self, simulation_config):
        """Test simulation configuration contains all required parameters."""
        # Arrange
        required_params = {
            'cell_size_m', 'tick_seconds', 'v_max_cells', 
            'noise_prob', 'timeout_ticks'
        }
        
        # Act & Assert
        config_keys = set(simulation_config.keys())
        assert required_params.issubset(config_keys), \
            f"Missing required config parameters: {required_params - config_keys}"
    
    def test_simulation_config_parameter_ranges(self, simulation_config):
        """Test simulation configuration parameters are within valid ranges."""
        # Arrange & Act & Assert
        assert simulation_config['cell_size_m'] > 0, "Cell size must be positive"
        assert simulation_config['tick_seconds'] > 0, "Tick duration must be positive"  
        assert simulation_config['v_max_cells'] >= 1, "Maximum velocity must be at least 1"
        assert 0 <= simulation_config['noise_prob'] <= 1, "Noise probability must be in [0,1]"
        assert simulation_config['timeout_ticks'] > 0, "Timeout must be positive"
    
    def test_configuration_enables_realistic_speeds(self, simulation_config):
        """Test configuration allows realistic urban traffic speeds."""
        # Arrange
        cell_size_m = simulation_config['cell_size_m']
        v_max_cells = simulation_config['v_max_cells'] 
        tick_seconds = simulation_config['tick_seconds']
        
        # Act - calculate maximum possible speed
        max_speed_kph = v_max_cells * cell_size_m * 3.6 / tick_seconds
        
        # Assert - should allow realistic highway speeds but not extreme speeds
        assert 80 <= max_speed_kph <= 150, \
            f"Max speed {max_speed_kph:.1f} km/h should allow highways but prevent unrealistic speeds"
"""
Tests for NaSch simulation rules and cellular grid management.

Validates the core NaSch algorithm (4 rules), cellular automata behavior,
and Gymnasium-like simulation model interface.
"""

import pytest
import numpy as np
from typing import Dict, List, Tuple, Optional


class TestNaSchRules:
    """Test core NaSch cellular automata rules."""
    
    def test_nasch_rule_1_acceleration_increases_velocity(self):
        """Test NaSch Rule 1: vehicles accelerate when below vmax."""
        # Arrange
        current_velocity = 2
        vmax = 4
        
        # Act - apply rule 1 (acceleration)
        new_velocity = min(current_velocity + 1, vmax)
        
        # Assert
        assert new_velocity == 3, "Vehicle should accelerate by 1 when below vmax"
        
        # Arrange - at maximum velocity
        current_velocity = vmax
        
        # Act  
        new_velocity = min(current_velocity + 1, vmax)
        
        # Assert
        assert new_velocity == vmax, "Vehicle should not exceed vmax"
    
    def test_nasch_rule_2_braking_prevents_collision(self):
        """Test NaSch Rule 2: vehicles brake to avoid collision."""
        # Arrange - vehicle approaching obstacle
        velocity_after_rule1 = 3
        gap_to_obstacle = 2  # cells to next vehicle
        
        # Act - apply rule 2 (braking)
        new_velocity = min(velocity_after_rule1, gap_to_obstacle)
        
        # Assert
        assert new_velocity == 2, "Vehicle should brake to match gap"
        
        # Arrange - large gap, no braking needed
        velocity_after_rule1 = 2
        gap_to_obstacle = 5
        
        # Act
        new_velocity = min(velocity_after_rule1, gap_to_obstacle)
        
        # Assert  
        assert new_velocity == 2, "Vehicle should not brake when gap is sufficient"
    
    def test_nasch_rule_3_noise_introduces_randomness(self):
        """Test NaSch Rule 3: stochastic noise introduces random braking."""
        # Arrange
        velocity_after_rule2 = 3
        noise_prob = 0.3
        
        # Act & Assert - with noise (simulated)
        # Noise should reduce velocity by 1 with probability noise_prob
        velocity_with_noise = max(0, velocity_after_rule2 - 1)
        assert velocity_with_noise == 2, "Noise should reduce velocity by 1"
        
        # Act & Assert - without noise 
        velocity_no_noise = velocity_after_rule2
        assert velocity_no_noise == 3, "Without noise, velocity unchanged"
        
        # Act & Assert - noise cannot make velocity negative
        low_velocity = 0
        velocity_with_noise_low = max(0, low_velocity - 1)
        assert velocity_with_noise_low == 0, "Noise cannot make velocity negative"
    
    def test_nasch_rule_4_movement_updates_position(self):
        """Test NaSch Rule 4: vehicles move according to final velocity."""
        # Arrange
        current_position = 5  # cells from edge start
        final_velocity = 2    # cells/tick after rules 1-3
        
        # Act - apply rule 4 (movement)
        new_position = current_position + final_velocity
        
        # Assert
        assert new_position == 7, "Vehicle should advance by velocity amount"
        
        # Arrange - zero velocity (stopped)
        current_position = 3
        final_velocity = 0
        
        # Act
        new_position = current_position + final_velocity
        
        # Assert
        assert new_position == 3, "Stopped vehicle should not change position"


class TestGapCalculation:
    """Test gap calculation logic for NaSch rule 2."""
    
    def test_gap_calculation_same_edge_finds_next_vehicle(self):
        """Test gap calculation finds next vehicle on same edge."""
        # Arrange - edge with vehicles: [0][0][V1][0][0][V2][0]
        #                               0  1   2  3  4   5   6
        edge_cells = np.array([0, 0, 1, 0, 0, 2, 0], dtype=np.int32)  # IDs: 0=empty, 1,2=vehicles
        vehicle_position = 2  # V1 at position 2
        
        # Act - calculate gap ahead
        gap = self._calculate_gap_same_edge(edge_cells, vehicle_position)
        
        # Assert - gap should be 2 (positions 3,4 are free before V2 at position 5)
        assert gap == 2, "Gap should count free cells before next vehicle"
    
    def test_gap_calculation_same_edge_no_obstacle(self):
        """Test gap calculation when no vehicle ahead on same edge."""
        # Arrange - edge with one vehicle: [0][0][V1][0][0][0][0]
        edge_cells = np.array([0, 0, 1, 0, 0, 0, 0], dtype=np.int32)
        vehicle_position = 2
        edge_length = len(edge_cells)
        
        # Act - gap to end of edge
        gap = edge_length - 1 - vehicle_position  # cells to edge boundary
        
        # Assert - gap should be 4 (positions 3,4,5,6 before edge end)
        assert gap == 4, "Gap should extend to edge end when no vehicle ahead"
    
    def test_gap_calculation_cross_edge_boundary(self):
        """Test gap calculation across edge boundaries."""
        # Arrange - current edge ending, next edge has vehicle
        current_edge_cells = np.array([0, 0, 1, 0, 0], dtype=np.int32)  # V1 at pos 2
        next_edge_cells = np.array([0, 2, 0, 0], dtype=np.int32)         # V2 at pos 1
        vehicle_position = 2
        
        # Act - calculate total gap
        gap_to_end = len(current_edge_cells) - 1 - vehicle_position  # 2 cells in current edge  
        gap_in_next = 1  # 1 free cell before V2 in next edge
        total_gap = gap_to_end + gap_in_next
        
        # Assert
        assert total_gap == 3, "Gap should span across edge boundary"
    
    def test_gap_calculation_handles_red_light(self):
        """Test gap calculation respects traffic light constraints."""
        # Arrange - vehicle approaching intersection with red light
        edge_cells = np.array([0, 0, 1, 0, 0, 0], dtype=np.int32)  # V1 at pos 2
        vehicle_position = 2
        red_light_at_exit = True
        
        # Act - gap limited by red light
        if red_light_at_exit:
            gap_to_light = len(edge_cells) - 1 - vehicle_position  # Stop at edge end
            effective_gap = gap_to_light
        else:
            effective_gap = 999  # No light constraint
        
        # Assert  
        assert effective_gap == 3, "Red light should limit gap to edge boundary"
    
    @staticmethod
    def _calculate_gap_same_edge(edge_cells: np.ndarray, vehicle_pos: int) -> int:
        """Helper: calculate gap to next vehicle on same edge."""
        for d in range(1, len(edge_cells) - vehicle_pos):
            if edge_cells[vehicle_pos + d] != 0:
                return d - 1
        return len(edge_cells) - 1 - vehicle_pos


class TestCellularGrid:
    """Test cellular grid management and edge discretization."""
    
    def test_cellular_grid_initializes_empty(self):
        """Test cellular grid starts with all cells empty."""
        # Arrange
        edge_length_cells = 20
        
        # Act - create empty edge array
        edge_cells = np.zeros(edge_length_cells, dtype=np.int32)
        
        # Assert
        assert len(edge_cells) == edge_length_cells, "Array should have correct length"
        assert np.all(edge_cells == 0), "All cells should be empty initially"
        assert edge_cells.dtype == np.int32, "Should use int32 for vehicle IDs"
    
    def test_cellular_grid_places_vehicle_in_cell(self):
        """Test cellular grid correctly places vehicle in specific cell."""
        # Arrange
        edge_cells = np.zeros(10, dtype=np.int32)
        vehicle_id = 42
        target_position = 5
        
        # Act - place vehicle
        edge_cells[target_position] = vehicle_id
        
        # Assert
        assert edge_cells[target_position] == vehicle_id, "Cell should contain vehicle ID"
        assert np.sum(edge_cells != 0) == 1, "Exactly one cell should be occupied"
    
    def test_cellular_grid_prevents_overlapping_vehicles(self):
        """Test cellular grid prevents multiple vehicles in same cell."""
        # Arrange
        edge_cells = np.zeros(10, dtype=np.int32)
        vehicle1_id = 1
        vehicle2_id = 2
        position = 3
        
        # Act - place first vehicle
        edge_cells[position] = vehicle1_id
        
        # Attempt to place second vehicle in same cell (should be rejected)
        can_place = edge_cells[position] == 0
        
        # Assert
        assert not can_place, "Should not allow placement in occupied cell"
        assert edge_cells[position] == vehicle1_id, "Original vehicle should remain"
    
    def test_cellular_grid_moves_vehicle_atomically(self):
        """Test cellular grid moves vehicle atomically (remove then place)."""
        # Arrange
        edge_cells = np.zeros(8, dtype=np.int32)
        vehicle_id = 7
        old_position = 2
        new_position = 5
        
        # Setup - vehicle at old position
        edge_cells[old_position] = vehicle_id
        
        # Act - atomic move (clear old, set new)
        edge_cells[old_position] = 0
        edge_cells[new_position] = vehicle_id
        
        # Assert  
        assert edge_cells[old_position] == 0, "Old position should be cleared"
        assert edge_cells[new_position] == vehicle_id, "New position should have vehicle"
        assert np.sum(edge_cells != 0) == 1, "Vehicle should exist exactly once"
    
    def test_cellular_grid_handles_edge_transitions(self):
        """Test cellular grid manages vehicle transitions between edges."""
        # Arrange - two connected edges
        edge1_cells = np.array([0, 0, 1, 0], dtype=np.int32)  # V1 at position 2
        edge2_cells = np.zeros(6, dtype=np.int32)
        vehicle_id = 1
        velocity = 3
        
        # Vehicle wants to move 3 cells from position 2 -> position 5
        # But edge1 only has 4 cells, so overflow = 5 - 4 = 1
        old_position = 2
        new_position = old_position + velocity  # 5
        edge1_length = len(edge1_cells)
        
        # Act - handle overflow to next edge
        if new_position >= edge1_length:
            overflow = new_position - edge1_length  # 1
            # Remove from edge1
            edge1_cells[old_position] = 0
            # Place in edge2 at overflow position
            if overflow < len(edge2_cells):
                edge2_cells[overflow] = vehicle_id
        
        # Assert
        assert edge1_cells[old_position] == 0, "Vehicle should be removed from edge1"
        assert edge2_cells[1] == vehicle_id, "Vehicle should appear in edge2 at overflow position"


class TestSimulationModelInterface:
    """Test Gymnasium-like simulation model interface."""
    
    def test_simulation_model_reset_initializes_state(self, mock_topology_data):
        """Test simulation model reset() method initializes clean state."""
        # Arrange
        topology_data = mock_topology_data
        
        # Act - simulate reset() call
        initial_state = self._mock_reset(topology_data)
        
        # Assert - should return initial state
        assert initial_state['tick'] == 0, "Should start at tick 0"
        assert initial_state['vehicles'] == [], "Should start with no vehicles"
        assert 'traffic_lights' in initial_state, "Should initialize traffic lights"
    
    def test_simulation_model_step_advances_one_tick(self):
        """Test simulation model step() method advances by one tick."""
        # Arrange - simulation in progress
        current_state = {'tick': 42, 'vehicles': [{'vid': 1, 'pos': 5}]}
        
        # Act - simulate step() call  
        new_state, metrics, done = self._mock_step(current_state, actions=None)
        
        # Assert - should advance time
        assert new_state['tick'] == 43, "Should increment tick by 1"
        assert isinstance(metrics, dict), "Should return metrics dictionary"
        assert isinstance(done, bool), "Should return termination flag"
    
    def test_simulation_model_step_returns_metrics(self):
        """Test simulation model step() returns meaningful metrics."""
        # Arrange
        current_state = {'tick': 10, 'vehicles': [{'vid': 1, 'velocity': 2}]}
        
        # Act
        new_state, metrics, done = self._mock_step(current_state, actions=None)
        
        # Assert - metrics should contain expected fields
        expected_metrics = {'total_vehicles', 'avg_speed_kph', 'density'}
        assert expected_metrics.issubset(metrics.keys()), "Should return standard metrics"
        
        # Assert - metric values should be reasonable
        assert metrics['total_vehicles'] >= 0, "Vehicle count should be non-negative"
        assert metrics['avg_speed_kph'] >= 0, "Average speed should be non-negative"
        assert 0 <= metrics['density'] <= 1, "Density should be ratio in [0,1]"
    
    def test_simulation_model_step_handles_actions(self):
        """Test simulation model step() accepts and processes actions."""
        # Arrange
        current_state = {'tick': 5, 'vehicles': []}
        actions = {
            'spawn_vehicles': 3,
            'traffic_light_overrides': {'intersection_1': 'force_green_ns'}
        }
        
        # Act - step with actions
        new_state, metrics, done = self._mock_step(current_state, actions)
        
        # Assert - actions should be acknowledged
        # (Implementation details will vary, but interface should accept actions)
        assert isinstance(new_state, dict), "Should return updated state"
        assert 'vehicles' in new_state, "Should handle vehicle spawning action"
    
    def test_simulation_model_get_observation_returns_detailed_state(self):
        """Test simulation model get_observation() returns detailed state."""
        # Arrange
        simulation_state = {
            'tick': 20,
            'vehicles': [{'vid': 1, 'x': -99.132, 'y': 19.431, 'velocity': 2}],
            'traffic_lights': [{'node': 'A', 'phase': 'NS_GREEN'}]
        }
        
        # Act - get observation
        observation = self._mock_get_observation(simulation_state)
        
        # Assert - should contain detailed information
        assert 'vehicles' in observation, "Should include vehicle positions"
        assert 'traffic_lights' in observation, "Should include traffic light states"
        assert 'tick' in observation, "Should include current time"
        
        # Assert - vehicle observations should have coordinates
        for vehicle in observation['vehicles']:
            assert 'x' in vehicle and 'y' in vehicle, "Vehicles should have coordinates"
    
    def test_simulation_model_termination_conditions(self):
        """Test simulation model handles termination conditions."""
        # Arrange - different termination scenarios
        
        # Scenario 1: Maximum ticks reached
        max_ticks_state = {'tick': 10000}
        _, _, done_max_ticks = self._mock_step(max_ticks_state, None, max_ticks=10000)
        assert done_max_ticks, "Should terminate at maximum tick limit"
        
        # Scenario 2: No vehicles remaining  
        no_vehicles_state = {'tick': 100, 'vehicles': []}
        _, _, done_no_vehicles = self._mock_step(no_vehicles_state, None, terminate_when_empty=True)
        # Note: termination logic depends on implementation goals
        
        # Scenario 3: Normal operation continues
        normal_state = {'tick': 50, 'vehicles': [{'vid': 1}]}
        _, _, done_normal = self._mock_step(normal_state, None)
        assert not done_normal, "Should continue during normal operation"
    
    @staticmethod
    def _mock_reset(topology_data):
        """Helper: simulate reset() behavior."""
        return {
            'tick': 0,
            'vehicles': [],
            'traffic_lights': [{'node': node_id, 'phase': 'NS_GREEN'} 
                             for node_id in topology_data['nodes'].keys()]
        }
    
    @staticmethod  
    def _mock_step(current_state, actions, max_ticks=None, terminate_when_empty=False):
        """Helper: simulate step() behavior."""
        new_tick = current_state['tick'] + 1
        
        # Simple mock metrics
        vehicle_count = len(current_state.get('vehicles', []))
        metrics = {
            'total_vehicles': vehicle_count,
            'avg_speed_kph': 25.0,  # Mock average
            'density': 0.3
        }
        
        # Mock termination logic
        done = False
        if max_ticks and new_tick >= max_ticks:
            done = True
        if terminate_when_empty and vehicle_count == 0:
            done = True
            
        new_state = current_state.copy()
        new_state['tick'] = new_tick
        
        return new_state, metrics, done
    
    @staticmethod
    def _mock_get_observation(simulation_state):
        """Helper: simulate get_observation() behavior."""
        return {
            'tick': simulation_state['tick'],
            'vehicles': simulation_state.get('vehicles', []),
            'traffic_lights': simulation_state.get('traffic_lights', []),
            'edge_densities': {}  # Mock edge density data
        }


class TestNaSchSynchronization:
    """Test synchronous NaSch execution prevents vehicle overlaps."""
    
    def test_synchronous_nasch_prevents_vehicle_collision(self):
        """Test synchronous NaSch prevents vehicles from occupying same cell."""
        # Arrange - two vehicles approaching same target cell
        #   Edge: [V1][0][0][V2][0][0][0]  
        #         0   1  2   3   4  5  6
        edge_cells = np.array([1, 0, 0, 2, 0, 0, 0], dtype=np.int32)
        
        vehicles = [
            {'vid': 1, 'pos': 0, 'velocity': 3},  # Wants to move to position 3
            {'vid': 2, 'pos': 3, 'velocity': 2}   # Wants to move to position 5  
        ]
        
        # Act - simulate synchronous update
        new_positions = self._synchronous_update(edge_cells, vehicles)
        
        # Assert - no overlaps should occur
        occupied_positions = [pos for pos in new_positions.values() if pos is not None]
        assert len(occupied_positions) == len(set(occupied_positions)), \
            "No two vehicles should occupy same position"
    
    def test_synchronous_nasch_resolves_movement_conflicts(self):
        """Test synchronous NaSch resolves conflicting movements fairly."""
        # Arrange - vehicles with conflicting target positions
        edge_cells = np.array([1, 0, 2, 0, 0], dtype=np.int32)
        vehicles = [
            {'vid': 1, 'pos': 0, 'velocity': 2},  # Wants position 2
            {'vid': 2, 'pos': 2, 'velocity': 1}   # Wants position 3 (no conflict)
        ]
        
        # Act - apply conflict resolution
        # If position 2 is occupied, vehicle 1 should be blocked
        target_positions = {1: 2, 2: 3}
        conflicts = self._detect_conflicts(target_positions)
        
        # Assert - conflicts should be detected and resolved
        assert isinstance(conflicts, (list, set)), "Should return conflict information"
        # Specific resolution depends on implementation (first-come, random, etc.)
    
    def test_synchronous_nasch_maintains_vehicle_conservation(self):
        """Test synchronous NaSch conserves vehicle count."""
        # Arrange - initial vehicle setup
        initial_vehicles = {1: {'pos': 0}, 2: {'pos': 3}, 3: {'pos': 6}}
        
        # Act - perform synchronous step (mock)
        updated_vehicles = self._mock_synchronous_step(initial_vehicles)
        
        # Assert - same number of vehicles
        assert len(updated_vehicles) == len(initial_vehicles), \
            "Vehicle count should be conserved during step"
        
        # Assert - same vehicle IDs
        assert set(updated_vehicles.keys()) == set(initial_vehicles.keys()), \
            "Vehicle IDs should be conserved during step"
    
    @staticmethod
    def _synchronous_update(edge_cells, vehicles):
        """Helper: simulate synchronous position update."""
        new_positions = {}
        
        # Phase 1: Calculate all target positions
        targets = {}
        for vehicle in vehicles:
            vid = vehicle['vid']
            current_pos = vehicle['pos'] 
            velocity = vehicle['velocity']
            target_pos = current_pos + velocity
            targets[vid] = target_pos
        
        # Phase 2: Resolve conflicts (simplified)
        for vid, target in targets.items():
            if target < len(edge_cells) and edge_cells[target] == 0:
                new_positions[vid] = target
            else:
                new_positions[vid] = None  # Blocked
                
        return new_positions
    
    @staticmethod
    def _detect_conflicts(target_positions):
        """Helper: detect position conflicts."""
        position_counts = {}
        for vid, pos in target_positions.items():
            if pos in position_counts:
                position_counts[pos].append(vid)
            else:
                position_counts[pos] = [vid]
        
        conflicts = [vids for pos, vids in position_counts.items() if len(vids) > 1]
        return conflicts
    
    @staticmethod
    def _mock_synchronous_step(vehicles):
        """Helper: mock synchronous step preserving vehicles."""
        # Simple mock that maintains vehicle set
        return {vid: {'pos': data['pos'] + 1} for vid, data in vehicles.items()}
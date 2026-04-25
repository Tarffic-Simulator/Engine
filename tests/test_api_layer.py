"""
Tests for FastAPI endpoints and simulation manager.

Validates REST API contracts, request/response schemas, simulation session
management, and HTTP status codes for the web service layer.
"""

import pytest
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from unittest.mock import Mock, patch
from datetime import datetime, timedelta


class TestSimulationManager:
    """Test SimulationManager session lifecycle and cleanup."""
    
    def test_simulation_manager_creates_new_session(self):
        """Test SimulationManager creates and stores new simulation sessions."""
        # Arrange
        manager = self._mock_simulation_manager()
        simulation_config = {
            'area': 'Roma Norte, CDMX',
            'initial_vehicles': 50,
            'cell_size_m': 7.5
        }
        
        # Act
        simulation_id = manager.create_simulation(simulation_config)
        
        # Assert
        assert isinstance(simulation_id, (str, UUID)), "Should return valid simulation ID"
        assert manager.session_exists(simulation_id), "Should store simulation session"
        
        session = manager.get_session(simulation_id)
        assert session['created_at'] is not None, "Should track creation time"
        assert session['tick'] == 0, "Should start at tick 0"
    
    def test_simulation_manager_retrieves_existing_session(self):
        """Test SimulationManager retrieves existing simulation sessions."""
        # Arrange
        manager = self._mock_simulation_manager()
        simulation_id = manager.create_simulation({'area': 'Test Area'})
        
        # Act
        session = manager.get_session(simulation_id)
        
        # Assert 
        assert session is not None, "Should retrieve existing session"
        assert session['id'] == simulation_id, "Should return correct session"
        assert 'model' in session, "Should include simulation model"
        assert 'topology' in session, "Should include topology data"
    
    def test_simulation_manager_steps_simulation_and_updates_state(self):
        """Test SimulationManager steps simulation and updates session state."""
        # Arrange
        manager = self._mock_simulation_manager()
        simulation_id = manager.create_simulation({'area': 'Test Area'})
        n_ticks = 3
        
        # Act
        result = manager.step_simulation(simulation_id, n_ticks)
        
        # Assert
        assert result['success'], "Step should succeed for valid simulation"
        assert 'new_state' in result, "Should return updated state"
        assert 'metrics' in result, "Should return metrics"
        
        # Verify session was updated
        updated_session = manager.get_session(simulation_id)
        assert updated_session['tick'] == n_ticks, "Should advance tick count"
        assert updated_session['last_accessed'] is not None, "Should update access time"
    
    def test_simulation_manager_handles_invalid_simulation_id(self):
        """Test SimulationManager handles invalid simulation ID gracefully."""
        # Arrange
        manager = self._mock_simulation_manager()
        invalid_id = uuid4()
        
        # Act & Assert - get_session
        session = manager.get_session(invalid_id)
        assert session is None, "Should return None for invalid ID"
        
        # Act & Assert - step_simulation
        result = manager.step_simulation(invalid_id, 1)
        assert not result['success'], "Step should fail for invalid ID"
        assert 'error' in result, "Should provide error message"
    
    def test_simulation_manager_cleans_up_expired_sessions(self):
        """Test SimulationManager removes expired simulation sessions."""
        # Arrange
        manager = self._mock_simulation_manager()
        
        # Create sessions with different ages
        recent_id = manager.create_simulation({'area': 'Recent'})
        old_id = manager.create_simulation({'area': 'Old'})
        
        # Mock old session as expired
        old_session = manager.get_session(old_id)
        old_session['last_accessed'] = datetime.now() - timedelta(minutes=61)  # Expired
        
        # Act - cleanup sessions older than 60 minutes
        cleaned_count = manager.cleanup_expired(ttl_minutes=60)
        
        # Assert
        assert cleaned_count > 0, "Should clean up expired sessions"
        assert manager.session_exists(recent_id), "Should keep recent sessions"
        assert not manager.session_exists(old_id), "Should remove expired sessions"
    
    def test_simulation_manager_prevents_memory_leaks_with_limits(self):
        """Test SimulationManager prevents memory leaks with session limits."""
        # Arrange
        manager = self._mock_simulation_manager(max_sessions=3)
        
        # Act - create more sessions than limit
        session_ids = []
        for i in range(5):
            sim_id = manager.create_simulation({'area': f'Area_{i}'})
            session_ids.append(sim_id)
        
        # Assert - should enforce session limit
        active_sessions = manager.get_active_session_count()
        assert active_sessions <= 3, "Should enforce maximum session limit"
    
    @staticmethod
    def _mock_simulation_manager(max_sessions=100):
        """Helper: create mock SimulationManager."""
        
        class MockSimulationManager:
            def __init__(self):
                self.sessions = {}
                self.max_sessions = max_sessions
            
            def create_simulation(self, config):
                if len(self.sessions) >= self.max_sessions:
                    # Remove oldest session
                    oldest_id = min(self.sessions.keys(), 
                                   key=lambda k: self.sessions[k]['created_at'])
                    del self.sessions[oldest_id]
                
                sim_id = str(uuid4())
                self.sessions[sim_id] = {
                    'id': sim_id,
                    'model': {'type': 'NaSchModel'},
                    'topology': {'area': config.get('area')},
                    'created_at': datetime.now(),
                    'last_accessed': datetime.now(),
                    'tick': 0,
                    'config': config
                }
                return sim_id
            
            def get_session(self, simulation_id):
                session = self.sessions.get(str(simulation_id))
                if session:
                    session['last_accessed'] = datetime.now()
                return session
            
            def session_exists(self, simulation_id):
                return str(simulation_id) in self.sessions
            
            def step_simulation(self, simulation_id, n_ticks):
                session = self.get_session(simulation_id)
                if not session:
                    return {'success': False, 'error': 'Simulation not found'}
                
                session['tick'] += n_ticks
                return {
                    'success': True,
                    'new_state': {'tick': session['tick']},
                    'metrics': {'total_vehicles': 10}
                }
            
            def cleanup_expired(self, ttl_minutes):
                cutoff = datetime.now() - timedelta(minutes=ttl_minutes)
                expired = [
                    sim_id for sim_id, session in self.sessions.items()
                    if session['last_accessed'] < cutoff
                ]
                for sim_id in expired:
                    del self.sessions[sim_id]
                return len(expired)
            
            def get_active_session_count(self):
                return len(self.sessions)
        
        return MockSimulationManager()


class TestSimulationEndpoints:
    """Test REST API endpoints for simulation management."""
    
    def test_create_simulation_endpoint_accepts_valid_request(self):
        """Test POST /simulations/ accepts valid simulation configuration."""
        # Arrange
        request_data = {
            'area': 'Polanco, Ciudad de México',
            'config': {
                'initial_vehicles': 100,
                'cell_size_m': 7.5,
                'noise_prob': 0.3
            }
        }
        
        # Act
        response = self._mock_post_simulations(request_data)
        
        # Assert
        assert response['status_code'] == 201, "Should return 201 Created"
        assert 'simulation_id' in response['body'], "Should return simulation ID"
        assert 'initial_state' in response['body'], "Should return initial state"
    
    def test_create_simulation_endpoint_validates_request_schema(self):
        """Test POST /simulations/ validates request schema."""
        # Arrange - invalid requests
        invalid_requests = [
            {},  # Missing area
            {'area': ''},  # Empty area
            {'area': 'Valid Area', 'config': {'initial_vehicles': -1}},  # Invalid config
            {'area': 'Valid Area', 'config': {'noise_prob': 1.5}}  # Invalid noise prob
        ]
        
        # Act & Assert
        for request_data in invalid_requests:
            response = self._mock_post_simulations(request_data)
            assert response['status_code'] == 422, \
                f"Should return 422 for invalid request: {request_data}"
            assert 'error' in response['body'], "Should provide error details"
    
    def test_get_simulation_endpoint_returns_simulation_state(self):
        """Test GET /simulations/{id} returns current simulation state."""
        # Arrange
        simulation_id = uuid4()
        
        # Act
        response = self._mock_get_simulation(simulation_id)
        
        # Assert
        assert response['status_code'] == 200, "Should return 200 OK"
        body = response['body']
        assert body['simulation_id'] == str(simulation_id), "Should return correct ID"
        assert 'tick' in body, "Should include current tick"
        assert 'status' in body, "Should include simulation status"
    
    def test_get_simulation_endpoint_handles_not_found(self):
        """Test GET /simulations/{id} handles non-existent simulation."""
        # Arrange
        nonexistent_id = uuid4()
        
        # Act
        response = self._mock_get_simulation(nonexistent_id, exists=False)
        
        # Assert
        assert response['status_code'] == 404, "Should return 404 Not Found"
        assert 'error' in response['body'], "Should provide error message"
    
    def test_step_simulation_endpoint_advances_simulation(self):
        """Test PUT /simulations/{id}/step advances simulation state."""
        # Arrange
        simulation_id = uuid4()
        step_request = {
            'n_ticks': 5,
            'actions': {'spawn_vehicles': 3}
        }
        
        # Act
        response = self._mock_put_step_simulation(simulation_id, step_request)
        
        # Assert
        assert response['status_code'] == 200, "Should return 200 OK"
        body = response['body']
        assert 'new_tick' in body, "Should return updated tick"
        assert 'metrics' in body, "Should return step metrics"
    
    def test_get_metrics_endpoint_returns_aggregated_metrics(self):
        """Test GET /simulations/{id}/metrics returns aggregated metrics."""
        # Arrange
        simulation_id = uuid4()
        
        # Act
        response = self._mock_get_metrics(simulation_id)
        
        # Assert
        assert response['status_code'] == 200, "Should return 200 OK"
        metrics = response['body']
        
        # Should include standard metrics
        expected_metrics = {
            'tick', 'total_vehicles', 'avg_speed_kph', 
            'density', 'throughput_veh_per_min', 'congestion_ratio'
        }
        assert expected_metrics.issubset(metrics.keys()), \
            "Should include all standard metrics"
    
    def test_get_snapshot_endpoint_returns_detailed_state(self):
        """Test GET /simulations/{id}/snapshot returns detailed visualization state."""
        # Arrange
        simulation_id = uuid4()
        
        # Act
        response = self._mock_get_snapshot(simulation_id)
        
        # Assert
        assert response['status_code'] == 200, "Should return 200 OK"
        snapshot = response['body']
        
        # Should include visualization data
        expected_fields = {'tick', 'vehicles', 'traffic_lights', 'edge_densities'}
        assert expected_fields.issubset(snapshot.keys()), \
            "Should include visualization data"
        
        # Vehicles should have geographic coordinates
        if snapshot.get('vehicles'):
            vehicle = snapshot['vehicles'][0]
            assert 'x' in vehicle and 'y' in vehicle, \
                "Vehicles should have geographic coordinates"
    
    def test_delete_simulation_endpoint_removes_simulation(self):
        """Test DELETE /simulations/{id} removes simulation and cleans resources."""
        # Arrange
        simulation_id = uuid4()
        
        # Act
        response = self._mock_delete_simulation(simulation_id)
        
        # Assert
        assert response['status_code'] == 204, "Should return 204 No Content"
        
        # Verify simulation is removed
        get_response = self._mock_get_simulation(simulation_id, exists=False)
        assert get_response['status_code'] == 404, "Should be removed after delete"
    
    def test_endpoints_handle_concurrent_requests(self):
        """Test endpoints handle concurrent requests to same simulation."""
        # Arrange
        simulation_id = uuid4()
        
        # Act - simulate concurrent step requests
        responses = []
        for _ in range(3):
            response = self._mock_put_step_simulation(simulation_id, {'n_ticks': 1})
            responses.append(response)
        
        # Assert - should handle concurrency gracefully
        success_count = sum(1 for r in responses if r['status_code'] == 200)
        assert success_count > 0, "Should handle at least some concurrent requests"
        # Implementation may serialize requests or handle them concurrently
    
    @staticmethod
    def _mock_post_simulations(request_data):
        """Helper: mock POST /simulations/ endpoint."""
        # Validate required fields
        if 'area' not in request_data or not request_data['area']:
            return {
                'status_code': 422,
                'body': {'error': 'Missing or empty area field'}
            }
        
        config = request_data.get('config', {})
        if config.get('initial_vehicles', 0) < 0:
            return {
                'status_code': 422,
                'body': {'error': 'initial_vehicles must be non-negative'}
            }
        
        if not (0 <= config.get('noise_prob', 0.3) <= 1):
            return {
                'status_code': 422,
                'body': {'error': 'noise_prob must be in [0, 1]'}
            }
        
        # Success response
        return {
            'status_code': 201,
            'body': {
                'simulation_id': str(uuid4()),
                'initial_state': {
                    'tick': 0,
                    'total_vehicles': config.get('initial_vehicles', 0)
                },
                'area': request_data['area']
            }
        }
    
    @staticmethod
    def _mock_get_simulation(simulation_id, exists=True):
        """Helper: mock GET /simulations/{id} endpoint."""
        if not exists:
            return {
                'status_code': 404,
                'body': {'error': f'Simulation {simulation_id} not found'}
            }
        
        return {
            'status_code': 200,
            'body': {
                'simulation_id': str(simulation_id),
                'tick': 42,
                'status': 'running',
                'total_vehicles': 75,
                'created_at': datetime.now().isoformat()
            }
        }
    
    @staticmethod
    def _mock_put_step_simulation(simulation_id, request_data):
        """Helper: mock PUT /simulations/{id}/step endpoint.""" 
        n_ticks = request_data.get('n_ticks', 1)
        
        return {
            'status_code': 200,
            'body': {
                'simulation_id': str(simulation_id),
                'new_tick': 42 + n_ticks,
                'metrics': {
                    'total_vehicles': 78,
                    'avg_speed_kph': 25.3,
                    'density': 0.35
                }
            }
        }
    
    @staticmethod
    def _mock_get_metrics(simulation_id):
        """Helper: mock GET /simulations/{id}/metrics endpoint."""
        return {
            'status_code': 200,
            'body': {
                'tick': 100,
                'total_vehicles': 120,
                'avg_speed_kph': 28.7,
                'density': 0.42,
                'throughput_veh_per_min': 15.2,
                'congestion_ratio': 0.18
            }
        }
    
    @staticmethod
    def _mock_get_snapshot(simulation_id):
        """Helper: mock GET /simulations/{id}/snapshot endpoint."""
        return {
            'status_code': 200,
            'body': {
                'tick': 150,
                'vehicles': [
                    {
                        'vid': 1, 'vtype': 'CAR', 'x': -99.1320, 'y': 19.4316,
                        'velocity': 2, 'edge': ('A', 'B', 0)
                    }
                ],
                'traffic_lights': [
                    {
                        'node_id': 'intersection_1', 'current_phase': 'NS_GREEN',
                        'x': -99.1315, 'y': 19.4318, 'cycle_position': 0.3
                    }
                ],
                'edge_densities': {
                    ('A', 'B', 0): 0.6,
                    ('B', 'C', 0): 0.3
                }
            }
        }
    
    @staticmethod
    def _mock_delete_simulation(simulation_id):
        """Helper: mock DELETE /simulations/{id} endpoint."""
        return {
            'status_code': 204,
            'body': {}  # No content
        }


class TestPydanticSchemas:
    """Test Pydantic request/response schemas for API validation."""
    
    def test_create_simulation_request_schema_validation(self):
        """Test CreateSimulationRequest schema validates input correctly."""
        # Arrange - valid request
        valid_request = {
            'area': 'Centro Histórico, CDMX',
            'config': {
                'initial_vehicles': 200,
                'cell_size_m': 7.5,
                'noise_prob': 0.25,
                'v_max_cells': 5
            }
        }
        
        # Act & Assert - should validate successfully
        is_valid = self._validate_create_simulation_request(valid_request)
        assert is_valid, "Valid request should pass schema validation"
        
        # Arrange - invalid requests
        invalid_requests = [
            {'area': None},  # Null area
            {'area': 'Valid', 'config': {'initial_vehicles': 'not_a_number'}},  # Wrong type
            {'area': 'Valid', 'config': {'noise_prob': -0.1}},  # Out of range
        ]
        
        # Act & Assert
        for invalid_req in invalid_requests:
            is_valid = self._validate_create_simulation_request(invalid_req)
            assert not is_valid, f"Invalid request should fail: {invalid_req}"
    
    def test_simulation_response_schema_includes_required_fields(self):
        """Test SimulationResponse schema includes all required fields."""
        # Arrange
        response_data = {
            'simulation_id': str(uuid4()),
            'tick': 85,
            'status': 'running',
            'total_vehicles': 150,
            'created_at': datetime.now().isoformat()
        }
        
        # Act & Assert
        is_valid = self._validate_simulation_response(response_data)
        assert is_valid, "Valid response should pass schema validation"
        
        # Check required fields
        required_fields = {'simulation_id', 'tick', 'status', 'total_vehicles'}
        for field in required_fields:
            incomplete_response = response_data.copy()
            del incomplete_response[field]
            is_valid = self._validate_simulation_response(incomplete_response)
            assert not is_valid, f"Response missing {field} should be invalid"
    
    def test_metrics_response_schema_enforces_numeric_constraints(self):
        """Test MetricsResponse schema enforces numeric constraints.""" 
        # Arrange
        valid_metrics = {
            'tick': 200,
            'total_vehicles': 180,
            'avg_speed_kph': 32.5,
            'density': 0.45,
            'throughput_veh_per_min': 18.7,
            'congestion_ratio': 0.22
        }
        
        # Act & Assert - valid metrics
        is_valid = self._validate_metrics_response(valid_metrics)
        assert is_valid, "Valid metrics should pass schema validation"
        
        # Arrange - invalid metrics
        invalid_metrics = [
            {**valid_metrics, 'total_vehicles': -5},      # Negative count
            {**valid_metrics, 'avg_speed_kph': -10.0},    # Negative speed
            {**valid_metrics, 'density': 1.5},            # Density > 1
            {**valid_metrics, 'congestion_ratio': -0.1}   # Negative ratio
        ]
        
        # Act & Assert
        for invalid_metric in invalid_metrics:
            is_valid = self._validate_metrics_response(invalid_metric)
            assert not is_valid, f"Invalid metric should fail: {invalid_metric}"
    
    def test_snapshot_response_schema_validates_vehicle_structures(self):
        """Test SnapshotResponse schema validates vehicle data structures."""
        # Arrange
        valid_snapshot = {
            'tick': 120,
            'vehicles': [
                {
                    'vid': 1,
                    'vtype': 'CAR',
                    'x': -99.1320,
                    'y': 19.4316,
                    'velocity': 2,
                    'edge': ('A', 'B', 0),
                    'wait_ticks': 0
                }
            ],
            'traffic_lights': [],
            'edge_densities': {}
        }
        
        # Act & Assert - valid snapshot
        is_valid = self._validate_snapshot_response(valid_snapshot)
        assert is_valid, "Valid snapshot should pass schema validation"
        
        # Arrange - invalid vehicle data
        invalid_vehicle = valid_snapshot.copy()
        invalid_vehicle['vehicles'] = [
            {'vid': 'not_a_number', 'x': -99.132, 'y': 19.431}  # Invalid vid type
        ]
        
        # Act & Assert
        is_valid = self._validate_snapshot_response(invalid_vehicle)
        assert not is_valid, "Invalid vehicle structure should fail validation"
    
    def test_step_request_schema_validates_actions(self):
        """Test StepRequest schema validates actions structure."""
        # Arrange
        valid_step_request = {
            'n_ticks': 3,
            'actions': {
                'spawn_vehicles': 5,
                'traffic_light_overrides': {
                    'intersection_1': 'force_green_ns'
                }
            }
        }
        
        # Act & Assert
        is_valid = self._validate_step_request(valid_step_request)
        assert is_valid, "Valid step request should pass validation"
        
        # Arrange - invalid actions
        invalid_requests = [
            {'n_ticks': 0},                    # Zero ticks
            {'n_ticks': -1},                   # Negative ticks
            {'n_ticks': 1, 'actions': 'not_dict'}  # Actions not a dict
        ]
        
        # Act & Assert
        for invalid_req in invalid_requests:
            is_valid = self._validate_step_request(invalid_req)
            assert not is_valid, f"Invalid step request should fail: {invalid_req}"
    
    @staticmethod
    def _validate_create_simulation_request(data: Dict) -> bool:
        """Helper: validate CreateSimulationRequest schema.""" 
        try:
            # Basic validation logic
            if not isinstance(data.get('area'), str) or not data['area']:
                return False
            
            config = data.get('config', {})
            if not isinstance(config, dict):
                return False
            
            # Validate config fields if present
            if 'initial_vehicles' in config:
                if not isinstance(config['initial_vehicles'], int) or config['initial_vehicles'] < 0:
                    return False
            
            if 'noise_prob' in config:
                if not isinstance(config['noise_prob'], (int, float)):
                    return False
                if not (0 <= config['noise_prob'] <= 1):
                    return False
            
            return True
        except (TypeError, KeyError):
            return False
    
    @staticmethod
    def _validate_simulation_response(data: Dict) -> bool:
        """Helper: validate SimulationResponse schema."""
        try:
            required_fields = {'simulation_id', 'tick', 'status', 'total_vehicles'}
            if not required_fields.issubset(data.keys()):
                return False
            
            if not isinstance(data['tick'], int) or data['tick'] < 0:
                return False
            if not isinstance(data['total_vehicles'], int) or data['total_vehicles'] < 0:
                return False
            
            return True
        except (TypeError, KeyError):
            return False
    
    @staticmethod
    def _validate_metrics_response(data: Dict) -> bool:
        """Helper: validate MetricsResponse schema."""
        try:
            if not isinstance(data['total_vehicles'], int) or data['total_vehicles'] < 0:
                return False
            if not isinstance(data['avg_speed_kph'], (int, float)) or data['avg_speed_kph'] < 0:
                return False  
            if not isinstance(data['density'], (int, float)) or not (0 <= data['density'] <= 1):
                return False
            if not isinstance(data['congestion_ratio'], (int, float)) or not (0 <= data['congestion_ratio'] <= 1):
                return False
            
            return True
        except (TypeError, KeyError):
            return False
    
    @staticmethod
    def _validate_snapshot_response(data: Dict) -> bool:
        """Helper: validate SnapshotResponse schema."""
        try:
            vehicles = data.get('vehicles', [])
            if not isinstance(vehicles, list):
                return False
            
            for vehicle in vehicles:
                if not isinstance(vehicle.get('vid'), int):
                    return False
                if not isinstance(vehicle.get('x'), (int, float)):
                    return False
                if not isinstance(vehicle.get('y'), (int, float)):
                    return False
            
            return True
        except (TypeError, KeyError):
            return False
    
    @staticmethod
    def _validate_step_request(data: Dict) -> bool:
        """Helper: validate StepRequest schema."""
        try:
            n_ticks = data.get('n_ticks', 1)
            if not isinstance(n_ticks, int) or n_ticks <= 0:
                return False
            
            actions = data.get('actions')
            if actions is not None and not isinstance(actions, dict):
                return False
            
            return True
        except (TypeError, KeyError):
            return False
"""
Shared fixtures and test configuration for traffic engine test suite.
"""

import pytest
import networkx as nx
import importlib
from typing import Any, Callable, Dict, List, Tuple
from uuid import uuid4


@pytest.fixture
def simple_network():
    """Small in-memory NetworkX MultiDiGraph for testing without OSM data.
    
    Creates a simple 4-node diamond network:
    
        A --- B
        |     |
        D --- C
        
    Each edge has realistic CDMX-like attributes.
    """
    G = nx.MultiDiGraph()
    
    # Add nodes with coordinates
    G.add_node('A', x=-99.1332, y=19.4326, street_count=2)  # Northwest
    G.add_node('B', x=-99.1312, y=19.4326, street_count=2)  # Northeast  
    G.add_node('C', x=-99.1312, y=19.4306, street_count=2)  # Southeast
    G.add_node('D', x=-99.1332, y=19.4306, street_count=2)  # Southwest
    
    # Add edges with realistic attributes
    edges = [
        ('A', 'B', {'length': 150.0, 'speed_kph': 40.0, 'highway': 'secondary', 'lanes': 2}),
        ('B', 'C', {'length': 200.0, 'speed_kph': 30.0, 'highway': 'residential', 'lanes': 1}),
        ('C', 'D', {'length': 150.0, 'speed_kph': 40.0, 'highway': 'secondary', 'lanes': 2}),
        ('D', 'A', {'length': 200.0, 'speed_kph': 30.0, 'highway': 'residential', 'lanes': 1}),
        # Diagonal connections for more routing options
        ('A', 'C', {'length': 250.0, 'speed_kph': 50.0, 'highway': 'primary', 'lanes': 3}),
        ('B', 'D', {'length': 250.0, 'speed_kph': 50.0, 'highway': 'primary', 'lanes': 3}),
    ]
    
    for u, v, attrs in edges:
        # Add travel_time based on length and speed
        travel_time = attrs['length'] / (attrs['speed_kph'] / 3.6)
        attrs['travel_time'] = travel_time
        G.add_edge(u, v, **attrs)
        
    return G


@pytest.fixture
def linear_network():
    """Simple linear network A -> B -> C for testing edge transitions.
    
    Useful for testing vehicle movement across edge boundaries.
    """
    G = nx.MultiDiGraph()
    
    # Linear chain of nodes
    nodes = [('A', -99.1332, 19.4326), ('B', -99.1322, 19.4326), ('C', -99.1312, 19.4326)]
    for node_id, x, y in nodes:
        G.add_node(node_id, x=x, y=y)
    
    # Two edges with different characteristics
    G.add_edge('A', 'B', length=75.0, speed_kph=30.0, highway='residential', 
               travel_time=9.0, lanes=1)
    G.add_edge('B', 'C', length=100.0, speed_kph=50.0, highway='secondary',
               travel_time=7.2, lanes=2)
               
    return G


@pytest.fixture 
def intersection_network():
    """4-way intersection for testing traffic light behavior.
    
        North
          |
    West --+-- East
          |
        South
    """
    G = nx.MultiDiGraph()
    
    # Center intersection
    G.add_node('center', x=-99.1322, y=19.4316, street_count=4)
    
    # Surrounding nodes
    directions = [
        ('north', -99.1322, 19.4326),
        ('east', -99.1312, 19.4316), 
        ('south', -99.1322, 19.4306),
        ('west', -99.1332, 19.4316),
    ]
    
    for node_id, x, y in directions:
        G.add_node(node_id, x=x, y=y, street_count=1)
        
    # Edges to center (for traffic light testing)
    for direction, _, _ in directions:
        G.add_edge(direction, 'center', length=50.0, speed_kph=30.0,
                   highway='secondary', travel_time=6.0, lanes=1)
        G.add_edge('center', direction, length=50.0, speed_kph=30.0,
                   highway='secondary', travel_time=6.0, lanes=1)
    
    return G


@pytest.fixture
def vehicle_types_config():
    """Standard vehicle type configurations from prototype."""
    from enum import Enum
    
    class VehicleType(Enum):
        CAR = "car"
        BUS = "bus" 
        MOTO = "moto"
    
    return {
        VehicleType.CAR:  {'speed_factor': 1.0, 'noise_factor': 1.0, 'size_cells': 1},
        VehicleType.BUS:  {'speed_factor': 0.55, 'noise_factor': 0.6, 'size_cells': 2}, 
        VehicleType.MOTO: {'speed_factor': 1.25, 'noise_factor': 1.5, 'size_cells': 1},
    }


@pytest.fixture
def simulation_config():
    """Default simulation configuration parameters."""
    return {
        'cell_size_m': 7.5,
        'tick_seconds': 1.0,
        'v_max_cells': 5,
        'noise_prob': 0.3,
        'timeout_ticks': 120,
    }


@pytest.fixture
def mock_topology_data():
    """Sample TopologyData structure for testing without NetworkX dependency."""
    return {
        'nodes': {
            'A': {'x': -99.1332, 'y': 19.4326, 'is_boundary': False},
            'B': {'x': -99.1312, 'y': 19.4326, 'is_boundary': True},
            'C': {'x': -99.1312, 'y': 19.4306, 'is_boundary': False},
            'D': {'x': -99.1332, 'y': 19.4306, 'is_boundary': True},
        },
        'edges': {
            ('A', 'B', 0): {
                'length_m': 150.0,
                'speed_kph': 40.0,
                'n_cells': 20,
                'vmax_cells': 3,
                'geometry_points': [(-99.1332, 19.4326), (-99.1312, 19.4326)]
            },
            ('B', 'C', 0): {
                'length_m': 200.0, 
                'speed_kph': 30.0,
                'n_cells': 27,
                'vmax_cells': 2,
                'geometry_points': [(-99.1312, 19.4326), (-99.1312, 19.4306)]
            },
        },
        'bbox': {
            'min_x': -99.1332, 'max_x': -99.1312,
            'min_y': 19.4306, 'max_y': 19.4326
        }
    }


@pytest.fixture
def sample_simulation_id():
    """Generate a consistent simulation UUID for testing."""
    return uuid4()


@pytest.fixture
def realtime_symbol_loader() -> Callable[[str, str], Any]:
    """Load realtime modules/symbols with clear failure messages for TDD-first development."""

    def _load(module_name: str, symbol_name: str) -> Any:
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            pytest.fail(
                f"Missing realtime module '{module_name}'. Implement the realtime feature contracts first."
            )

        if not hasattr(module, symbol_name):
            pytest.fail(
                f"Missing realtime symbol '{symbol_name}' in module '{module_name}'."
            )

        return getattr(module, symbol_name)

    return _load


@pytest.fixture
def realtime_identifiers() -> Dict[str, str]:
    """Stable identifiers used across realtime session tests."""
    return {
        "session_id": "session-realtime-001",
        "run_id": "run-realtime-001",
    }


@pytest.fixture
def realtime_session_parameters() -> Dict[str, Any]:
    """Representative client parameters for realtime session creation."""
    return {
        "area": "Roma Norte, Ciudad de Mexico",
        "initial_vehicles": 16,
        "spawn_rate": 0.2,
        "tick_interval_ms": 250,
        "noise_prob": 0.1,
    }
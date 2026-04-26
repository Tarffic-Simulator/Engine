"""Domain models for traffic simulation engine."""

from .topology import TopologyData, NodeData, EdgeData, BoundingBox, NodeId, EdgeId, Coordinates
from .vehicles import (
    Vehicle, VehicleState, VehicleType, VehicleTypeConfig,
    PublicTransport,
    VEHICLE_TYPE_CONFIGS
)
from .traffic_lights import (
    TrafficLight, LightState, 
    calculate_bearing, is_ns_orientation
)
from .simulation_state import (
    SimulationState, Metrics, SnapshotData, StepResult
)

__all__ = [
    # Topology
    'TopologyData', 'NodeData', 'EdgeData', 'BoundingBox', 
    'NodeId', 'EdgeId', 'Coordinates',
    
    # Vehicles
    'Vehicle', 'VehicleState', 'VehicleType', 'VehicleTypeConfig',
    'PublicTransport',
    'VEHICLE_TYPE_CONFIGS',
    
    # Traffic lights
    'TrafficLight', 'LightState', 
    'calculate_bearing', 'is_ns_orientation',
    
    # Simulation state
    'SimulationState', 'Metrics', 'SnapshotData', 'StepResult',
]
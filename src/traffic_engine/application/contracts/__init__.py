"""Application contracts and DTOs."""

from .provider_interfaces import TopologyProvider, TrafficLightProvider
from .realtime_entities import RealtimeRunRecord, RealtimeSessionRecord, RealtimeTickRecord, RunStatus, SessionStatus
from .realtime_persistence import SimulationRunRepository, SimulationSessionRepository, SimulationTickRepository
from .realtime_runtime import RunExecutor, SimulationRuntimeGateway, SupportsShutdown
from .realtime_streaming import TickStreamBroker
from .simulation_dto import *

__all__ = [
    'TopologyProvider',
    'TrafficLightProvider',
    'CreateSimulationRequest',
    'CreateSimulationResponse',
    'StepSimulationRequest',
    'StepSimulationResponse',
    'GetMetricsRequest',
    'GetMetricsResponse',
    'GetSnapshotRequest',
    'GetSnapshotResponse',
    'SimulationConfigDto',
    'RealtimeSessionRecord',
    'RealtimeRunRecord',
    'RealtimeTickRecord',
    'SessionStatus',
    'RunStatus',
    'SimulationSessionRepository',
    'SimulationRunRepository',
    'SimulationTickRepository',
    'RunExecutor',
    'SimulationRuntimeGateway',
    'SupportsShutdown',
    'TickStreamBroker',
]
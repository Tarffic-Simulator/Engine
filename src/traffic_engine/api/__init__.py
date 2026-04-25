"""
Traffic Engine API Layer.

Provides REST API interfaces and request/response handling for the
traffic simulation engine, managing multiple concurrent simulations.
"""

from .simulation_manager import SimulationManager, SimulationInstance

__all__ = ['SimulationManager', 'SimulationInstance']
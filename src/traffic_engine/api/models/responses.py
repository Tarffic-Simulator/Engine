"""
Pydantic models for API responses.

Defines the response schemas for the FastAPI endpoints, providing structured
and validated responses for client consumption.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """Base response model with success indicator and error message."""
    success: bool = Field(description="Whether the operation was successful")
    error: Optional[str] = Field(None, description="Error message if success is False")


class CreateSimulationResponse(BaseResponse):
    """
    Response model for simulation creation.
    """
    simulation_id: str = Field(description="Unique identifier for the new simulation")
    initial_state: Dict[str, Any] = Field(
        description="Initial simulation state after setup",
        example={
            "tick": 0,
            "total_vehicles": 0,
            "active_vehicles": 0,
            "vehicle_count": 0,
            "traffic_light_count": 5
        }
    )
    topology_summary: Dict[str, Any] = Field(
        description="Brief summary of loaded topology",
        example={
            "nodes_count": 150,
            "edges_count": 320,
            "boundary_nodes": 12,
            "total_cells": 6400,
            "avg_edge_length_m": 85.5
        }
    )
    traffic_lights_count: int = Field(description="Number of traffic lights configured")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "simulation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "initial_state": {
                    "tick": 0,
                    "total_vehicles": 0,
                    "active_vehicles": 0,
                    "vehicle_count": 0,
                    "traffic_light_count": 8
                },
                "topology_summary": {
                    "nodes_count": 127,
                    "edges_count": 245,
                    "boundary_nodes": 15,
                    "total_cells": 4900,
                    "avg_edge_length_m": 95.2
                },
                "traffic_lights_count": 8
            }
        }


class StepSimulationResponse(BaseResponse):
    """
    Response model for simulation stepping.
    """
    simulation_id: str = Field(description="Simulation identifier")
    new_tick: int = Field(description="Simulation tick after step")
    metrics: Dict[str, Any] = Field(
        description="Aggregated performance metrics",
        example={
            "tick": 15,
            "total_vehicles": 45,
            "active_vehicles": 42,
            "average_speed": 0.72,
            "average_density": 0.15,
            "throughput": 0.35,
            "congestion_ratio": 0.08
        }
    )
    vehicles_spawned: int = Field(description="Number of new vehicles added")
    vehicles_removed: int = Field(description="Number of vehicles that exited")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "simulation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "new_tick": 25,
                "metrics": {
                    "tick": 25,
                    "total_vehicles": 67,
                    "active_vehicles": 64,
                    "average_speed": 0.68,
                    "congestion_ratio": 0.12,
                    "throughput": 0.42
                },
                "vehicles_spawned": 3,
                "vehicles_removed": 1
            }
        }


class GetMetricsResponse(BaseResponse):
    """
    Response model for simulation metrics.
    """
    simulation_id: str = Field(description="Simulation identifier")
    current_metrics: Dict[str, Any] = Field(
        description="Current tick performance metrics",
        example={
            "tick": 100,
            "total_vehicles": 150,
            "average_speed": 0.65,
            "congestion_ratio": 0.25,
            "performance_grade": "good"
        }
    )
    history: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Historical metrics if requested"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "simulation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "current_metrics": {
                    "tick": 150,
                    "total_vehicles": 180,
                    "active_vehicles": 175,
                    "average_speed": 0.61,
                    "average_density": 0.32,
                    "congestion_ratio": 0.28,
                    "performance_grade": "fair"
                }
            }
        }


class GetSnapshotResponse(BaseResponse):
    """
    Response model for simulation snapshot.
    """
    simulation_id: str = Field(description="Simulation identifier")
    snapshot: Dict[str, Any] = Field(
        description="Complete simulation snapshot data",
        example={
            "meta": {
                "tick": 50,
                "total_vehicles": 85,
                "active_vehicles": 82,
                "simulation_time_s": 50
            },
            "vehicles": [
                {
                    "id": "vehicle_001",
                    "type": "car",
                    "edge_id": "('1', '2', 0)",
                    "cell_position": 15,
                    "velocity": 2
                }
            ],
            "traffic_lights": [
                {
                    "node_id": "intersection_1",
                    "phase": "NS_GREEN",
                    "x": -99.1456,
                    "y": 19.4234,
                    "cycle_position": 0.3
                }
            ]
        }
    )
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "simulation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "snapshot": {
                    "meta": {
                        "tick": 75,
                        "total_vehicles": 92,
                        "active_vehicles": 89
                    },
                    "vehicles": [
                        {
                            "id": "v_001", 
                            "type": "car",
                            "velocity": 3,
                            "cell_position": 22
                        }
                    ],
                    "traffic_lights": []
                }
            }
        }


class SimulationListResponse(BaseResponse):
    """
    Response model for listing simulations.
    """
    simulations: Dict[str, Dict[str, Any]] = Field(
        description="Dictionary of simulation IDs to basic info",
        example={
            "sim1": {
                "created_at": 1640995200.0,
                "last_accessed": 1640995800.0,
                "is_initialized": True,
                "is_completed": False
            }
        }
    )
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "simulations": {
                    "a1b2c3d4-e5f6-7890-abcd-ef1234567890": {
                        "created_at": 1640995200.0,
                        "last_accessed": 1640995800.0,
                        "is_initialized": True,
                        "is_completed": False
                    }
                }
            }
        }


class ManagerStatsResponse(BaseResponse):
    """
    Response model for simulation manager statistics.
    """
    stats: Dict[str, Any] = Field(
        description="Manager statistics",
        example={
            "active_simulations": 3,
            "initialized_simulations": 3,
            "completed_simulations": 1,
            "max_concurrent": 10
        }
    )
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "stats": {
                    "active_simulations": 5,
                    "initialized_simulations": 5,
                    "completed_simulations": 2,
                    "max_concurrent": 10,
                    "last_cleanup": 1640995200.0
                }
            }
        }


class HealthResponse(BaseModel):
    """
    Response model for health check endpoint.
    """
    status: str = Field(description="Service status")
    version: str = Field(description="API version")
    timestamp: str = Field(description="Current timestamp")
    dependencies: Dict[str, str] = Field(
        description="Status of external dependencies",
        example={
            "osmnx": "available",
            "networkx": "available"
        }
    )
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2024-01-01T12:00:00Z",
                "dependencies": {
                    "osmnx": "available",
                    "networkx": "available"
                }
            }
        }
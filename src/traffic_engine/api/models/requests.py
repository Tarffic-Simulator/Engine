"""
Pydantic models for API requests.

Defines the request schemas for the FastAPI endpoints, providing validation
and documentation for client requests.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator


class CreateSimulationRequest(BaseModel):
    """
    Request model for creating a new simulation.
    """
    area: Optional[str] = Field(
        None, 
        description="Named geographic area (e.g., 'Roma Norte, Ciudad de México')",
        example="Polanco, Ciudad de México"
    )
    bbox: Optional[Dict[str, float]] = Field(
        None,
        description="Geographic bounding box with min_x, max_x, min_y, max_y",
        example={
            "min_x": -99.2000,
            "max_x": -99.1800,
            "min_y": 19.4200,
            "max_y": 19.4400
        }
    )
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional simulation configuration overrides",
        example={
            "initial_vehicles": 10,
            "max_vehicles": 500,
            "spawn_rate": 0.05,
            "noise_prob": 0.25
        }
    )
    
    @validator('bbox')
    def validate_bbox(cls, v):
        if v is not None:
            required_keys = {'min_x', 'max_x', 'min_y', 'max_y'}
            if not all(key in v for key in required_keys):
                raise ValueError(f"bbox must contain all keys: {required_keys}")
            if v['min_x'] >= v['max_x'] or v['min_y'] >= v['max_y']:
                raise ValueError("bbox min values must be less than max values")
        return v
    
    @validator('config')
    def validate_config(cls, v):
        if v:
            # Validate specific config parameters if provided
            if 'noise_prob' in v:
                noise_prob = v['noise_prob']
                if not (0 <= noise_prob <= 1):
                    raise ValueError("noise_prob must be between 0 and 1")
            
            if 'spawn_rate' in v and v['spawn_rate'] < 0:
                raise ValueError("spawn_rate must be non-negative")
            
            if 'max_vehicles' in v and v['max_vehicles'] < 1:
                raise ValueError("max_vehicles must be positive")
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "area": "Polanco, Ciudad de México",
                "config": {
                    "initial_vehicles": 50,
                    "max_vehicles": 1000,
                    "spawn_rate": 0.08,
                    "noise_prob": 0.28
                }
            }
        }


class StepSimulationRequest(BaseModel):
    """
    Request model for stepping a simulation.
    """
    n_ticks: int = Field(
        1, 
        ge=1, 
        le=100,
        description="Number of simulation ticks to advance",
        example=5
    )
    actions: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional actions to apply during step",
        example={
            "traffic_lights": {
                "intersection_1": {"cycle_ticks": 40}
            },
            "spawn_vehicles": {"count": 3}
        }
    )
    
    class Config:
        schema_extra = {
            "example": {
                "n_ticks": 10,
                "actions": {
                    "traffic_lights": {
                        "node_123": {"green_ratio": 0.6}
                    }
                }
            }
        }


class GetMetricsRequest(BaseModel):
    """
    Request model for retrieving simulation metrics.
    """
    include_history: bool = Field(
        False,
        description="Whether to include historical metric trends"
    )
    window_ticks: int = Field(
        60,
        ge=1,
        le=1000,
        description="Number of recent ticks to include in history"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "include_history": True,
                "window_ticks": 100
            }
        }


class GetSnapshotRequest(BaseModel):
    """
    Request model for retrieving simulation snapshot.
    """
    include_vehicle_details: bool = Field(
        True,
        description="Whether to include detailed vehicle information"
    )
    include_edge_data: bool = Field(
        True,
        description="Whether to include edge-level traffic data"
    )
    vehicle_types_filter: Optional[List[str]] = Field(
        None,
        description="Optional filter for specific vehicle types",
        example=["car", "truck"]
    )
    
    class Config:
        schema_extra = {
            "example": {
                "include_vehicle_details": True,
                "include_edge_data": False,
                "vehicle_types_filter": ["car"]
            }
        }
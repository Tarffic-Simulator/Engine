"""Domain entities for geographic areas and NaSch simulations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Tuple


NodeId = str
EdgeId = Tuple[NodeId, NodeId, int]
Coordinates = Tuple[float, float]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class BoundingBox:
    min_x: float
    max_x: float
    min_y: float
    max_y: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "min_x": self.min_x,
            "max_x": self.max_x,
            "min_y": self.min_y,
            "max_y": self.max_y,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "BoundingBox":
        return cls(
            min_x=float(payload["min_x"]),
            max_x=float(payload["max_x"]),
            min_y=float(payload["min_y"]),
            max_y=float(payload["max_y"]),
        )


@dataclass(frozen=True)
class NodeData:
    x: float
    y: float
    is_boundary: bool

    def to_dict(self) -> Dict[str, Any]:
        return {"x": self.x, "y": self.y, "is_boundary": self.is_boundary}

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "NodeData":
        return cls(
            x=float(payload["x"]),
            y=float(payload["y"]),
            is_boundary=bool(payload.get("is_boundary", False)),
        )


@dataclass(frozen=True)
class EdgeData:
    length_m: float
    speed_kph: float
    travel_time_sec: float
    n_cells: int
    vmax_cells: int
    geometry_points: List[Coordinates]

    def to_dict(self, edge_id: EdgeId) -> Dict[str, Any]:
        return {
            "u": edge_id[0],
            "v": edge_id[1],
            "key": edge_id[2],
            "length_m": self.length_m,
            "speed_kph": self.speed_kph,
            "travel_time_sec": self.travel_time_sec,
            "n_cells": self.n_cells,
            "vmax_cells": self.vmax_cells,
            "geometry_points": [list(point) for point in self.geometry_points],
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "EdgeData":
        return cls(
            length_m=float(payload["length_m"]),
            speed_kph=float(payload["speed_kph"]),
            travel_time_sec=float(payload["travel_time_sec"]),
            n_cells=int(payload["n_cells"]),
            vmax_cells=int(payload["vmax_cells"]),
            geometry_points=[(float(x), float(y)) for x, y in payload["geometry_points"]],
        )


@dataclass(frozen=True)
class TopologyData:
    nodes: Dict[NodeId, NodeData]
    edges: Dict[EdgeId, EdgeData]
    bbox: BoundingBox

    def outgoing_edges(self) -> Dict[NodeId, List[EdgeId]]:
        adjacency: Dict[NodeId, List[EdgeId]] = {node_id: [] for node_id in self.nodes}
        for edge_id in self.edges:
            adjacency.setdefault(edge_id[0], []).append(edge_id)
        return adjacency

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": {node_id: data.to_dict() for node_id, data in self.nodes.items()},
            "edges": [edge.to_dict(edge_id) for edge_id, edge in self.edges.items()],
            "bbox": self.bbox.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "TopologyData":
        nodes = {node_id: NodeData.from_dict(node) for node_id, node in payload["nodes"].items()}
        edges: Dict[EdgeId, EdgeData] = {}
        for edge_payload in payload["edges"]:
            edge_id: EdgeId = (
                str(edge_payload["u"]),
                str(edge_payload["v"]),
                int(edge_payload["key"]),
            )
            edges[edge_id] = EdgeData.from_dict(edge_payload)
        return cls(nodes=nodes, edges=edges, bbox=BoundingBox.from_dict(payload["bbox"]))


@dataclass(frozen=True)
class GeographicArea:
    area_id: str
    name: str
    topology: TopologyData
    created_at: datetime = field(default_factory=utc_now)

    @property
    def node_count(self) -> int:
        return len(self.topology.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.topology.edges)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "area_id": self.area_id,
            "name": self.name,
            "created_at": self.created_at,
            "topology": self.topology.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "GeographicArea":
        return cls(
            area_id=str(payload["area_id"]),
            name=str(payload["name"]),
            created_at=payload.get("created_at") or utc_now(),
            topology=TopologyData.from_dict(payload["topology"]),
        )


class SimulationStatus(str, Enum):
    RUNNING = "running"
    FINISHED = "finished"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class SimulationConfig:
    initial_vehicles: int
    max_vehicles: int
    max_steps: int
    spawn_rate: float
    noise_prob: float
    seed: int
    tick_interval_ms: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_vehicles": self.initial_vehicles,
            "max_vehicles": self.max_vehicles,
            "max_steps": self.max_steps,
            "spawn_rate": self.spawn_rate,
            "noise_prob": self.noise_prob,
            "seed": self.seed,
            "tick_interval_ms": self.tick_interval_ms,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "SimulationConfig":
        return cls(
            initial_vehicles=int(payload["initial_vehicles"]),
            max_vehicles=int(payload["max_vehicles"]),
            max_steps=int(payload["max_steps"]),
            spawn_rate=float(payload["spawn_rate"]),
            noise_prob=float(payload["noise_prob"]),
            seed=int(payload["seed"]),
            tick_interval_ms=int(payload["tick_interval_ms"]),
        )


@dataclass
class Vehicle:
    vid: int
    route: List[EdgeId]
    edge_idx: int = 0
    cell_pos: int = 0
    velocity: int = 0
    distance_traveled_m: float = 0.0
    wait_ticks: int = 0

    @property
    def current_edge(self) -> EdgeId:
        return self.route[self.edge_idx]

    @property
    def next_edge(self) -> EdgeId | None:
        next_index = self.edge_idx + 1
        if next_index >= len(self.route):
            return None
        return self.route[next_index]


@dataclass(frozen=True)
class VehicleSnapshot:
    id: int
    edge: EdgeId
    x: float
    y: float
    velocity: int
    speed_kph: float
    wait_ticks: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "edge": list(self.edge),
            "x": self.x,
            "y": self.y,
            "velocity": self.velocity,
            "speed_kph": self.speed_kph,
            "wait_ticks": self.wait_ticks,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "VehicleSnapshot":
        return cls(
            id=int(payload["id"]),
            edge=(str(payload["edge"][0]), str(payload["edge"][1]), int(payload["edge"][2])),
            x=float(payload["x"]),
            y=float(payload["y"]),
            velocity=int(payload["velocity"]),
            speed_kph=float(payload["speed_kph"]),
            wait_ticks=int(payload["wait_ticks"]),
        )


@dataclass(frozen=True)
class SimulationState:
    step_number: int
    vehicles: List[VehicleSnapshot]
    total_vehicles: int
    active_vehicles: int
    density: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "vehicles": [vehicle.to_dict() for vehicle in self.vehicles],
            "total_vehicles": self.total_vehicles,
            "active_vehicles": self.active_vehicles,
            "density": self.density,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "SimulationState":
        return cls(
            step_number=int(payload["step_number"]),
            vehicles=[VehicleSnapshot.from_dict(vehicle) for vehicle in payload["vehicles"]],
            total_vehicles=int(payload["total_vehicles"]),
            active_vehicles=int(payload["active_vehicles"]),
            density=float(payload["density"]),
        )


@dataclass(frozen=True)
class SimulationMetrics:
    step_number: int
    total_vehicles: int
    avg_speed_kph: float
    density: float
    throughput_veh_per_min: float
    congestion_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "total_vehicles": self.total_vehicles,
            "avg_speed_kph": self.avg_speed_kph,
            "density": self.density,
            "throughput_veh_per_min": self.throughput_veh_per_min,
            "congestion_ratio": self.congestion_ratio,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "SimulationMetrics":
        return cls(
            step_number=int(payload["step_number"]),
            total_vehicles=int(payload["total_vehicles"]),
            avg_speed_kph=float(payload["avg_speed_kph"]),
            density=float(payload["density"]),
            throughput_veh_per_min=float(payload["throughput_veh_per_min"]),
            congestion_ratio=float(payload["congestion_ratio"]),
        )


@dataclass(frozen=True)
class SimulationRecord:
    simulation_id: str
    area_id: str
    status: SimulationStatus
    config: SimulationConfig
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    latest_step: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "area_id": self.area_id,
            "status": self.status.value,
            "config": self.config.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "latest_step": self.latest_step,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "SimulationRecord":
        return cls(
            simulation_id=str(payload["simulation_id"]),
            area_id=str(payload["area_id"]),
            status=SimulationStatus(payload["status"]),
            config=SimulationConfig.from_dict(payload["config"]),
            created_at=payload.get("created_at") or utc_now(),
            updated_at=payload.get("updated_at") or utc_now(),
            latest_step=int(payload.get("latest_step", 0)),
        )


@dataclass(frozen=True)
class SimulationStep:
    simulation_id: str
    step_number: int
    metrics: SimulationMetrics
    state: SimulationState
    recorded_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "step_number": self.step_number,
            "metrics": self.metrics.to_dict(),
            "state": self.state.to_dict(),
            "recorded_at": self.recorded_at,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "SimulationStep":
        return cls(
            simulation_id=str(payload["simulation_id"]),
            step_number=int(payload["step_number"]),
            metrics=SimulationMetrics.from_dict(payload["metrics"]),
            state=SimulationState.from_dict(payload["state"]),
            recorded_at=payload.get("recorded_at") or utc_now(),
        )


def count_boundary_nodes(nodes: Iterable[NodeData]) -> int:
    return sum(1 for node in nodes if node.is_boundary)

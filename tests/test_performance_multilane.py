"""Lightweight performance sanity tests for multilane grid operations."""

from __future__ import annotations

import importlib
import time
from types import SimpleNamespace
from typing import Any, Tuple

import numpy as np
import pytest


EdgeId = Tuple[str, str, int]


def _load_symbol(module_name: str, symbol_name: str) -> Any:
    """Load symbol for performance contracts with clear failure context."""
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        pytest.fail(f"Missing module '{module_name}' required by performance tests: {exc}")

    if not hasattr(module, symbol_name):
        pytest.fail(f"Missing symbol '{symbol_name}' in module '{module_name}'.")

    return getattr(module, symbol_name)


def _build_topology_with_capacity(n_lanes: int, n_cells: int) -> Tuple[Any, EdgeId]:
    """Create a deterministic topology fixture with enough slots for 500 vehicles."""
    topology_module = importlib.import_module("traffic_engine.domain.models.topology")
    NodeData = getattr(topology_module, "NodeData")
    BoundingBox = getattr(topology_module, "BoundingBox")
    TopologyData = getattr(topology_module, "TopologyData")

    edge_id: EdgeId = ("N0", "N1", 0)
    topology = TopologyData(
        nodes={
            "N0": NodeData(x=-99.1332, y=19.4326, is_boundary=True),
            "N1": NodeData(x=-99.1322, y=19.4326, is_boundary=True),
        },
        edges={
            edge_id: SimpleNamespace(
                length_m=float(n_cells * 7.5),
                speed_kph=50.0,
                n_cells=n_cells,
                vmax_cells=3,
                geometry_points=[(-99.1332, 19.4326), (-99.1322, 19.4326)],
                n_lanes=n_lanes,
            )
        },
        bbox=BoundingBox(
            min_x=-99.1332,
            max_x=-99.1322,
            min_y=19.4326,
            max_y=19.4326,
        ),
    )
    return topology, edge_id


def _populate_multilane_grid(
    grid: Any,
    edge_id: EdgeId,
    vehicle_count: int,
    lane_count: int,
) -> None:
    """Populate a deterministic set of vehicle placements for timing checks."""
    for vehicle_id in range(1, vehicle_count + 1):
        lane_index = (vehicle_id - 1) % lane_count
        cell_index = (vehicle_id - 1) // lane_count
        grid.place_vehicle(
            edge_id=edge_id,
            lane_index=lane_index,
            position=cell_index,
            vehicle_id=vehicle_id,
        )


class TestMultilanePerformance:
    """Performance checks that remain deterministic and CI-friendly."""

    def test_multilane_grid_population_for_500_vehicles_stays_within_reasonable_budget(self) -> None:
        """Lane-aware occupancy operations should handle 500 vehicles without slowdowns."""
        # Arrange
        cellular_grid_cls = _load_symbol(
            "traffic_engine.domain.simulation.cellular_grid",
            "CellularGrid",
        )
        topology, edge_id = _build_topology_with_capacity(n_lanes=3, n_cells=600)
        grid = cellular_grid_cls(topology)

        # Act
        start_time = time.perf_counter()
        _populate_multilane_grid(
            grid=grid,
            edge_id=edge_id,
            vehicle_count=500,
            lane_count=3,
        )
        elapsed_seconds = time.perf_counter() - start_time
        occupied_slots = int(np.sum(grid.edge_cells[edge_id] > 0))

        # Assert
        assert (occupied_slots, elapsed_seconds < 1.0) == (500, True)

    def test_multilane_grid_after_population_keeps_lane_indexes_in_range_and_no_collisions(self) -> None:
        """Large multilane population should keep occupancy valid without lane-index leakage."""
        # Arrange
        cellular_grid_cls = _load_symbol(
            "traffic_engine.domain.simulation.cellular_grid",
            "CellularGrid",
        )
        lane_count = 4
        topology, edge_id = _build_topology_with_capacity(n_lanes=lane_count, n_cells=300)
        grid = cellular_grid_cls(topology)

        # Act
        _populate_multilane_grid(
            grid=grid,
            edge_id=edge_id,
            vehicle_count=500,
            lane_count=lane_count,
        )
        occupancy = grid.edge_cells[edge_id]
        lanewise_vehicle_counts = [int(np.sum(occupancy[lane_index] > 0)) for lane_index in range(lane_count)]

        # Assert
        assert (
            occupancy.shape[0] == lane_count,
            int(np.sum(occupancy > 0)) == 500,
            min(lanewise_vehicle_counts) > 0,
        ) == (True, True, True)
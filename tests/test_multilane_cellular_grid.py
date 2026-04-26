"""Contract tests for multilane lane-major cellular grid behavior."""

from __future__ import annotations

import importlib
import inspect
from types import SimpleNamespace
from typing import Any, Tuple

import pytest


EdgeId = Tuple[str, str, int]


def _load_symbol(module_name: str, symbol_name: str) -> Any:
    """Load a symbol and raise a focused test failure if unavailable."""
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        pytest.fail(f"Missing module '{module_name}' required by multilane grid tests: {exc}")

    if not hasattr(module, symbol_name):
        pytest.fail(f"Missing symbol '{symbol_name}' in module '{module_name}'.")

    return getattr(module, symbol_name)


def _build_topology_with_lanes(n_lanes: int, n_cells: int) -> Tuple[Any, EdgeId]:
    """Construct a topology object with lane metadata without implementation coupling."""
    topology_module = importlib.import_module("traffic_engine.domain.models.topology")
    NodeData = getattr(topology_module, "NodeData")
    BoundingBox = getattr(topology_module, "BoundingBox")
    TopologyData = getattr(topology_module, "TopologyData")

    edge_id: EdgeId = ("A", "B", 0)
    topology = TopologyData(
        nodes={
            "A": NodeData(x=-99.1332, y=19.4326, is_boundary=True),
            "B": NodeData(x=-99.1322, y=19.4326, is_boundary=True),
        },
        edges={
            edge_id: SimpleNamespace(
                length_m=float(n_cells * 7.5),
                speed_kph=40.0,
                n_cells=n_cells,
                vmax_cells=2,
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


class TestMultilaneCellularGrid:
    """Test-first contracts for 2D lane-major occupancy arrays."""

    def test_grid_initialization_when_edge_has_multiple_lanes_creates_lane_major_2d_array(
        self,
    ) -> None:
        """Multilane occupancy must be represented as [lane_index, cell_index]."""
        # Arrange
        cellular_grid_cls = _load_symbol(
            "traffic_engine.domain.simulation.cellular_grid",
            "CellularGrid",
        )
        topology, edge_id = _build_topology_with_lanes(n_lanes=3, n_cells=12)

        # Act
        grid = cellular_grid_cls(topology)
        shape = tuple(grid.edge_cells[edge_id].shape)

        # Assert
        assert shape == (3, 12)

    def test_place_vehicle_signature_includes_lane_index_for_multilane_addressing(self) -> None:
        """Placement API should expose lane_index explicitly for deterministic writes."""
        # Arrange
        cellular_grid_cls = _load_symbol(
            "traffic_engine.domain.simulation.cellular_grid",
            "CellularGrid",
        )

        # Act
        signature = inspect.signature(cellular_grid_cls.place_vehicle)

        # Assert
        assert "lane_index" in signature.parameters

    def test_place_vehicle_when_lane_index_is_out_of_bounds_raises_value_error(self) -> None:
        """Invalid lane writes should fail fast to protect occupancy integrity."""
        # Arrange
        cellular_grid_cls = _load_symbol(
            "traffic_engine.domain.simulation.cellular_grid",
            "CellularGrid",
        )
        topology, edge_id = _build_topology_with_lanes(n_lanes=2, n_cells=10)
        grid = cellular_grid_cls(topology)

        # Act / Assert
        with pytest.raises(ValueError):
            grid.place_vehicle(edge_id=edge_id, lane_index=4, position=0, vehicle_id=91)

    def test_find_free_cells_when_lane_is_requested_returns_positions_for_that_lane_only(self) -> None:
        """Free-cell lookup should isolate lane occupancy to avoid cross-lane artifacts."""
        # Arrange
        cellular_grid_cls = _load_symbol(
            "traffic_engine.domain.simulation.cellular_grid",
            "CellularGrid",
        )
        topology, edge_id = _build_topology_with_lanes(n_lanes=2, n_cells=8)
        grid = cellular_grid_cls(topology)

        # Act
        grid.place_vehicle(edge_id=edge_id, lane_index=0, position=0, vehicle_id=17)
        free_positions = grid.find_free_cells(edge_id=edge_id, lane_index=1, count=3)

        # Assert
        assert free_positions == [0, 1, 2]

    def test_move_vehicle_atomic_signature_is_lane_aware_for_origin_and_target(self) -> None:
        """Movement API should expose lane origin/target to avoid implicit lane jumps."""
        # Arrange
        cellular_grid_cls = _load_symbol(
            "traffic_engine.domain.simulation.cellular_grid",
            "CellularGrid",
        )

        # Act
        signature = inspect.signature(cellular_grid_cls.move_vehicle_atomic)

        # Assert
        assert {
            "old_lane_index",
            "new_lane_index",
        }.issubset(set(signature.parameters.keys()))

    def test_place_vehicle_when_target_lane_cell_is_occupied_rejects_conflict(self) -> None:
        """Conflicting writes in the same lane/cell should be rejected deterministically."""
        # Arrange
        cellular_grid_cls = _load_symbol(
            "traffic_engine.domain.simulation.cellular_grid",
            "CellularGrid",
        )
        topology, edge_id = _build_topology_with_lanes(n_lanes=2, n_cells=6)
        grid = cellular_grid_cls(topology)

        # Act
        first_placement = grid.place_vehicle(
            edge_id=edge_id,
            lane_index=1,
            position=3,
            vehicle_id=100,
        )
        second_placement = grid.place_vehicle(
            edge_id=edge_id,
            lane_index=1,
            position=3,
            vehicle_id=200,
        )

        # Assert
        assert (first_placement, second_placement) == (True, False)

    def test_move_vehicle_atomic_when_target_lane_cell_is_occupied_rejects_move(self) -> None:
        """Lane-aware atomic movement should fail when target lane/cell is occupied."""
        # Arrange
        cellular_grid_cls = _load_symbol(
            "traffic_engine.domain.simulation.cellular_grid",
            "CellularGrid",
        )
        topology, edge_id = _build_topology_with_lanes(n_lanes=2, n_cells=8)
        grid = cellular_grid_cls(topology)
        grid.place_vehicle(edge_id=edge_id, lane_index=0, position=2, vehicle_id=11)
        grid.place_vehicle(edge_id=edge_id, lane_index=1, position=4, vehicle_id=22)

        # Act
        moved = grid.move_vehicle_atomic(
            old_edge=edge_id,
            old_lane_index=0,
            old_position=2,
            new_edge=edge_id,
            new_lane_index=1,
            new_position=4,
            vehicle_id=11,
        )

        # Assert
        assert moved is False
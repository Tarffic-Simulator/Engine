"""Contract tests for lane-aware snapshot payload serialization."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any, Dict

import pytest

from traffic_engine.application.contracts import GetSnapshotRequest
from traffic_engine.application.use_cases.get_snapshot import GetSnapshotUseCase
from traffic_engine.domain.simulation import NaSchSimulationModel


class _FakeSimulationModel:
    """Deterministic simulation model double for snapshot serialization tests."""

    def __init__(self) -> None:
        self._state = SimpleNamespace(
            tick=12,
            vehicles=[
                SimpleNamespace(
                    vid=70,
                    vtype=SimpleNamespace(value="bus"),
                    edge=("A", "B", 0),
                    x=-99.1325,
                    y=19.4321,
                    velocity=1,
                    speed_kmh=9.0,
                    wait_ticks=0,
                    lane_index=1,
                    lateral_offset_m=1.75,
                    render_label="BUS",
                    render_color="#f39c12",
                )
            ],
            traffic_lights=[],
            total_vehicles=1,
            active_vehicles=1,
        )
        self._edge_states: Dict[Any, Dict[str, Any]] = {
            ("A", "B", 0): {
                "vehicle_count": 1,
                "density": 0.25,
                "average_speed": 9.0,
                "flow": 1.0,
                "n_lanes": 2,
                "occupancy_cells": [70, 0, 0],
                "occupancy_cells_lane_major": [[0, 70, 0], [0, 0, 0]],
            }
        }

    def get_state(self) -> Any:
        return self._state

    def get_edge_states(self) -> Dict[Any, Dict[str, Any]]:
        return self._edge_states


class TestSnapshotLanePayloads:
    """Snapshot contract tests for lane and bus visualization fields."""

    def test_get_snapshot_when_vehicle_has_lane_metadata_includes_lane_fields(self) -> None:
        """Lane index and lateral offsets should be present in vehicle payloads."""
        # Arrange
        use_case = GetSnapshotUseCase(simulation_model=_FakeSimulationModel())
        request = GetSnapshotRequest(
            include_vehicle_details=False,
            include_edge_data=True,
            vehicle_types_filter=None,
        )

        # Act
        response = use_case.execute(simulation_id="sim-lane-001", request=request)
        vehicle_payload = response.snapshot["vehicles"][0]

        # Assert
        assert {"lane_index", "lateral_offset_m"}.issubset(set(vehicle_payload.keys()))

    def test_get_snapshot_when_vehicle_is_bus_includes_render_label_and_color(self) -> None:
        """BUS payloads should carry stable label and color metadata for rendering."""
        # Arrange
        use_case = GetSnapshotUseCase(simulation_model=_FakeSimulationModel())
        request = GetSnapshotRequest(
            include_vehicle_details=True,
            include_edge_data=False,
            vehicle_types_filter=None,
        )

        # Act
        response = use_case.execute(simulation_id="sim-lane-002", request=request)
        vehicle_payload = response.snapshot["vehicles"][0]

        # Assert
        assert (
            vehicle_payload.get("render_label"),
            vehicle_payload.get("render_color"),
        ) == ("BUS", "#f39c12")

    def test_get_snapshot_when_edge_data_is_requested_includes_lane_count_and_lane_major_occupancy(
        self,
    ) -> None:
        """Edge payloads should expose lane-aware occupancy for downstream visualization."""
        # Arrange
        use_case = GetSnapshotUseCase(simulation_model=_FakeSimulationModel())
        request = GetSnapshotRequest(
            include_vehicle_details=False,
            include_edge_data=True,
            vehicle_types_filter=None,
        )

        # Act
        response = use_case.execute(simulation_id="sim-lane-003", request=request)
        edge_payload = response.snapshot["edges"]["('A', 'B', 0)"]

        # Assert
        assert (
            "n_lanes" in edge_payload,
            "occupancy_cells_lane_major" in edge_payload,
        ) == (True, True)

    def test_get_snapshot_when_edge_has_single_lane_exposes_n_lanes_without_breaking_shape(self) -> None:
        """Single-lane edges should still provide additive lane-aware payload fields."""
        # Arrange
        use_case = GetSnapshotUseCase(simulation_model=_FakeSimulationModel())
        request = GetSnapshotRequest(
            include_vehicle_details=False,
            include_edge_data=True,
            vehicle_types_filter=None,
        )
        model_state = use_case.simulation_model.get_state()
        model_state.vehicles[0].lane_index = 0
        edge_state = use_case.simulation_model.get_edge_states()[("A", "B", 0)]
        edge_state["n_lanes"] = 1
        edge_state["occupancy_cells_lane_major"] = [[70, 0, 0]]

        # Act
        response = use_case.execute(simulation_id="sim-lane-004", request=request)
        vehicle_payload = response.snapshot["vehicles"][0]
        edge_payload = response.snapshot["edges"]["('A', 'B', 0)"]

        # Assert
        assert (
            vehicle_payload.get("lane_index"),
            edge_payload.get("n_lanes"),
            len(edge_payload.get("occupancy_cells_lane_major", [])),
        ) == (0, 1, 1)

    def test_get_snapshot_when_using_nasch_model_does_not_log_missing_edge_states_warning(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """NaSch model should satisfy edge-state contract consumed by snapshot edge payloads."""
        # Arrange
        use_case = GetSnapshotUseCase(simulation_model=NaSchSimulationModel(seed=19))
        request = GetSnapshotRequest(
            include_vehicle_details=False,
            include_edge_data=True,
            vehicle_types_filter=None,
        )

        # Act
        with caplog.at_level(logging.WARNING, logger="traffic_engine.application.use_cases.get_snapshot"):
            response = use_case.execute(simulation_id="sim-contract-005", request=request)

        # Assert
        assert response.success is True
        assert "Could not retrieve edge states" not in caplog.text
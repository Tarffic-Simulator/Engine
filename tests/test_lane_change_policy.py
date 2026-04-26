"""Contract tests for multilane lane-change decision policy."""

from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import inspect
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

import numpy as np
import pytest


EdgeId = Tuple[str, str, int]


def _load_lane_change_symbols() -> Tuple[Any, Any]:
    """Load lane-change module symbols with explicit TDD-first failures."""
    module_name = "traffic_engine.domain.simulation.lane_change_policy"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        pytest.fail(f"Missing lane-change policy module '{module_name}': {exc}")

    if not hasattr(module, "check_lane_change"):
        pytest.fail("Missing 'check_lane_change' function in lane_change_policy module.")
    if not hasattr(module, "LaneChangeDecision"):
        pytest.fail("Missing 'LaneChangeDecision' model in lane_change_policy module.")

    return getattr(module, "check_lane_change"), getattr(module, "LaneChangeDecision")


def _invoke_check_lane_change(
    check_lane_change: Any,
    *,
    vehicle: Any,
    grid: Any,
    topology: Any,
    tick: int,
) -> Any:
    """Invoke decision logic with signature compatibility across implementations."""
    candidate_kwargs: Dict[str, Any] = {
        "vehicle": vehicle,
        "grid": grid,
        "topology": topology,
        "tick": tick,
        "rng": np.random.default_rng(7),
    }
    signature = inspect.signature(check_lane_change)
    accepted_kwargs = {
        name: candidate_kwargs[name]
        for name in signature.parameters
        if name in candidate_kwargs
    }
    return check_lane_change(**accepted_kwargs)


@dataclass
class _FakeVehicle:
    lane_index: int
    cell_pos: int
    velocity: int
    impatience_ticks: int = 0
    edge_idx: int = 0
    route: List[EdgeId] = field(default_factory=lambda: [("A", "B", 0)])

    @property
    def current_edge(self) -> EdgeId:
        return self.route[self.edge_idx]


class _FakeGrid:
    def __init__(self, edge_id: EdgeId, occupancy: np.ndarray) -> None:
        self.edge_cells = {edge_id: occupancy}


class TestLaneChangePolicy:
    """Test-first behavior contracts for safety and incentive lane changes."""

    def test_check_lane_change_when_target_lane_has_unsafe_rear_gap_returns_safety_blocked(
        self,
    ) -> None:
        """Safety checks should reject lane changes when rear gap is unsafe."""
        # Arrange
        check_lane_change, _ = _load_lane_change_symbols()
        edge_id: EdgeId = ("A", "B", 0)
        occupancy = np.zeros((2, 12), dtype=np.int32)
        occupancy[0, 5] = 101
        occupancy[1, 4] = 202
        vehicle = _FakeVehicle(lane_index=0, cell_pos=5, velocity=2, impatience_ticks=0)
        grid = _FakeGrid(edge_id=edge_id, occupancy=occupancy)
        topology = SimpleNamespace(edges={edge_id: SimpleNamespace(n_cells=12, n_lanes=2)})

        # Act
        decision = _invoke_check_lane_change(
            check_lane_change,
            vehicle=vehicle,
            grid=grid,
            topology=topology,
            tick=10,
        )

        # Assert
        assert (
            getattr(decision, "reason", None),
            getattr(decision, "target_lane_index", None),
        ) == ("safety_blocked", None)

    def test_check_lane_change_when_target_lane_has_unsafe_front_gap_returns_safety_blocked(
        self,
    ) -> None:
        """Safety checks should reject lane changes when front gap is unsafe."""
        # Arrange
        check_lane_change, _ = _load_lane_change_symbols()
        edge_id: EdgeId = ("A", "B", 0)
        occupancy = np.zeros((2, 12), dtype=np.int32)
        occupancy[0, 5] = 101
        occupancy[1, 6] = 303
        vehicle = _FakeVehicle(lane_index=0, cell_pos=5, velocity=2, impatience_ticks=0)
        grid = _FakeGrid(edge_id=edge_id, occupancy=occupancy)
        topology = SimpleNamespace(edges={edge_id: SimpleNamespace(n_cells=12, n_lanes=2)})

        # Act
        decision = _invoke_check_lane_change(
            check_lane_change,
            vehicle=vehicle,
            grid=grid,
            topology=topology,
            tick=11,
        )

        # Assert
        assert (
            getattr(decision, "reason", None),
            getattr(decision, "target_lane_index", None),
        ) == ("safety_blocked", None)

    def test_check_lane_change_when_current_lane_is_blocked_and_target_lane_safe_returns_preventive(
        self,
    ) -> None:
        """Preventive incentives should move vehicles away from imminent blockage."""
        # Arrange
        check_lane_change, _ = _load_lane_change_symbols()
        edge_id: EdgeId = ("A", "B", 0)
        occupancy = np.zeros((2, 12), dtype=np.int32)
        occupancy[0, 5] = 101
        occupancy[0, 6] = 301
        vehicle = _FakeVehicle(lane_index=0, cell_pos=5, velocity=2, impatience_ticks=0)
        grid = _FakeGrid(edge_id=edge_id, occupancy=occupancy)
        topology = SimpleNamespace(edges={edge_id: SimpleNamespace(n_cells=12, n_lanes=2)})

        # Act
        decision = _invoke_check_lane_change(
            check_lane_change,
            vehicle=vehicle,
            grid=grid,
            topology=topology,
            tick=25,
        )

        # Assert
        assert (
            getattr(decision, "reason", None),
            getattr(decision, "target_lane_index", None),
        ) == ("preventive", 1)

    def test_check_lane_change_when_impatience_is_high_and_change_is_safe_returns_aggressive(
        self,
    ) -> None:
        """High impatience should allow aggressive decision mode within safety bounds."""
        # Arrange
        check_lane_change, _ = _load_lane_change_symbols()
        edge_id: EdgeId = ("A", "B", 0)
        occupancy = np.zeros((2, 14), dtype=np.int32)
        occupancy[0, 6] = 111
        occupancy[0, 7] = 302
        vehicle = _FakeVehicle(lane_index=0, cell_pos=6, velocity=2, impatience_ticks=15)
        grid = _FakeGrid(edge_id=edge_id, occupancy=occupancy)
        topology = SimpleNamespace(edges={edge_id: SimpleNamespace(n_cells=14, n_lanes=2)})

        # Act
        decision = _invoke_check_lane_change(
            check_lane_change,
            vehicle=vehicle,
            grid=grid,
            topology=topology,
            tick=40,
        )

        # Assert
        assert (
            getattr(decision, "reason", None),
            getattr(decision, "target_lane_index", None),
        ) == ("aggressive", 1)

    def test_check_lane_change_when_impatience_threshold_not_reached_does_not_return_aggressive(
        self,
    ) -> None:
        """Aggressive mode should activate only after the impatience threshold is reached."""
        # Arrange
        check_lane_change, _ = _load_lane_change_symbols()
        edge_id: EdgeId = ("A", "B", 0)
        occupancy = np.zeros((2, 14), dtype=np.int32)
        occupancy[0, 6] = 111
        occupancy[0, 7] = 302
        vehicle = _FakeVehicle(lane_index=0, cell_pos=6, velocity=2, impatience_ticks=2)
        grid = _FakeGrid(edge_id=edge_id, occupancy=occupancy)
        topology = SimpleNamespace(edges={edge_id: SimpleNamespace(n_cells=14, n_lanes=2)})

        # Act
        decision = _invoke_check_lane_change(
            check_lane_change,
            vehicle=vehicle,
            grid=grid,
            topology=topology,
            tick=5,
        )

        # Assert
        assert getattr(decision, "reason", None) != "aggressive"

    def test_lane_change_decision_when_reason_is_invalid_raises_value_error(self) -> None:
        """Decision model should validate reason values to avoid contract drift."""
        # Arrange
        _, lane_change_decision_cls = _load_lane_change_symbols()

        # Act / Assert
        with pytest.raises(ValueError):
            lane_change_decision_cls(
                target_lane_index=1,
                reason="unsupported",
                safety_front_gap_cells=3,
                safety_rear_gap_cells=2,
            )
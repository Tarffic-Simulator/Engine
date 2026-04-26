"""Lane change policy for multilane NaSch simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

_ALLOWED_REASONS = {"stay", "safety_blocked", "preventive", "aggressive"}
_AGGRESSIVE_IMPATIENCE_THRESHOLD = 12


@dataclass(frozen=True)
class LaneChangeDecision:
    """Lane-change decision result.

    Attributes:
        target_lane_index: Destination lane index when a lane change is approved.
        reason: Decision reason category.
        safety_front_gap_cells: Front gap measured in the evaluated target lane.
        safety_rear_gap_cells: Rear gap measured in the evaluated target lane.
    """

    target_lane_index: Optional[int]
    reason: str
    safety_front_gap_cells: int
    safety_rear_gap_cells: int

    def __post_init__(self) -> None:
        """Validate reason values to keep contracts stable."""
        if self.reason not in _ALLOWED_REASONS:
            raise ValueError(
                f"Invalid lane-change reason '{self.reason}'. Expected one of {sorted(_ALLOWED_REASONS)}."
            )


def check_lane_change(
    vehicle: Any,
    grid: Any,
    topology: Any,
    tick: int,
    rng: Optional[np.random.Generator] = None,
) -> LaneChangeDecision:
    """Evaluate whether a vehicle should change lanes.

    Args:
        vehicle: Vehicle-like object with lane and kinematic state.
        grid: Grid-like object exposing lane-major occupancy as `edge_cells`.
        topology: Topology-like object exposing edge metadata.
        tick: Current simulation tick.
        rng: Optional random generator for future stochastic tie-breaking.

    Returns:
        LaneChangeDecision describing the chosen action.
    """
    del tick, rng

    edge_id = _resolve_current_edge(vehicle)
    if edge_id is None:
        return LaneChangeDecision(
            target_lane_index=None,
            reason="stay",
            safety_front_gap_cells=0,
            safety_rear_gap_cells=0,
        )

    occupancy = _resolve_edge_occupancy(grid=grid, edge_id=edge_id)
    if occupancy is None or occupancy.ndim != 2 or occupancy.shape[0] <= 1:
        return LaneChangeDecision(
            target_lane_index=None,
            reason="stay",
            safety_front_gap_cells=0,
            safety_rear_gap_cells=0,
        )

    lane_index = int(getattr(vehicle, "lane_index", 0))
    lane_index = max(0, min(lane_index, occupancy.shape[0] - 1))
    cell_pos = int(getattr(vehicle, "cell_pos", 0))
    velocity = max(0, int(getattr(vehicle, "velocity", 0)))
    impatience_ticks = max(0, int(getattr(vehicle, "impatience_ticks", 0)))

    current_lane_cells = occupancy[lane_index]
    current_front_gap = _front_gap(current_lane_cells, cell_pos)
    blocked_current_lane = current_front_gap <= velocity

    aggressive_mode = (
        blocked_current_lane and impatience_ticks >= _AGGRESSIVE_IMPATIENCE_THRESHOLD
    )
    rear_gap_required = max(0, velocity - (1 if aggressive_mode else 0))
    front_gap_required = max(1, velocity - (1 if aggressive_mode else 0))

    best_target_lane: Optional[int] = None
    best_front_gap = -1
    best_rear_gap = -1
    had_adjacent_lane = False

    for target_lane_index in (lane_index - 1, lane_index + 1):
        if target_lane_index < 0 or target_lane_index >= occupancy.shape[0]:
            continue

        had_adjacent_lane = True
        target_lane_cells = occupancy[target_lane_index]
        target_front_gap = _front_gap(target_lane_cells, cell_pos)
        target_rear_gap = _rear_gap(target_lane_cells, cell_pos)
        target_cell_free = _is_cell_free(target_lane_cells, cell_pos)

        is_safe = (
            target_cell_free
            and target_front_gap >= front_gap_required
            and target_rear_gap >= rear_gap_required
        )
        if not is_safe:
            continue

        if target_front_gap > best_front_gap:
            best_target_lane = target_lane_index
            best_front_gap = target_front_gap
            best_rear_gap = target_rear_gap

    if best_target_lane is None:
        if had_adjacent_lane:
            return LaneChangeDecision(
                target_lane_index=None,
                reason="safety_blocked",
                safety_front_gap_cells=max(0, best_front_gap),
                safety_rear_gap_cells=max(0, best_rear_gap),
            )
        return LaneChangeDecision(
            target_lane_index=None,
            reason="stay",
            safety_front_gap_cells=0,
            safety_rear_gap_cells=0,
        )

    if not blocked_current_lane and best_front_gap <= current_front_gap:
        return LaneChangeDecision(
            target_lane_index=None,
            reason="stay",
            safety_front_gap_cells=best_front_gap,
            safety_rear_gap_cells=best_rear_gap,
        )

    reason = "aggressive" if aggressive_mode else "preventive"
    return LaneChangeDecision(
        target_lane_index=best_target_lane,
        reason=reason,
        safety_front_gap_cells=best_front_gap,
        safety_rear_gap_cells=best_rear_gap,
    )


def _resolve_current_edge(vehicle: Any) -> Optional[Any]:
    current_edge = getattr(vehicle, "current_edge", None)
    if current_edge is not None:
        return current_edge

    route = getattr(vehicle, "route", None)
    edge_idx = getattr(vehicle, "edge_idx", None)
    if isinstance(route, list) and isinstance(edge_idx, int) and 0 <= edge_idx < len(route):
        return route[edge_idx]

    return None


def _resolve_edge_occupancy(grid: Any, edge_id: Any) -> Optional[np.ndarray]:
    edge_cells = getattr(grid, "edge_cells", {})
    occupancy = edge_cells.get(edge_id)
    if occupancy is None:
        return None
    return np.asarray(occupancy)


def _front_gap(lane_cells: np.ndarray, cell_pos: int) -> int:
    if cell_pos >= lane_cells.size - 1:
        return 0

    for index in range(cell_pos + 1, lane_cells.size):
        if lane_cells[index] != 0:
            return index - cell_pos - 1

    return lane_cells.size - cell_pos - 1


def _rear_gap(lane_cells: np.ndarray, cell_pos: int) -> int:
    if cell_pos <= 0:
        return 0

    for index in range(cell_pos - 1, -1, -1):
        if lane_cells[index] != 0:
            return cell_pos - index - 1

    return cell_pos


def _is_cell_free(lane_cells: np.ndarray, cell_pos: int) -> bool:
    if cell_pos < 0 or cell_pos >= lane_cells.size:
        return False
    return bool(lane_cells[cell_pos] == 0)

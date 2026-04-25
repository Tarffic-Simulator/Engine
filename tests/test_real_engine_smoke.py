"""Minimal smoke test against the real traffic_engine implementation."""

from traffic_engine.domain.models import BoundingBox, EdgeData, NodeData, TopologyData
from traffic_engine.domain.simulation import NaSchSimulationModel


def test_real_engine_reset_and_step_returns_state_and_metrics() -> None:
    """Reset the real model on a tiny topology and advance one tick."""
    topology = TopologyData(
        nodes={
            "A": NodeData(x=-99.15, y=19.43, is_boundary=True),
            "B": NodeData(x=-99.14, y=19.43, is_boundary=False),
            "C": NodeData(x=-99.14, y=19.44, is_boundary=True),
        },
        edges={
            ("A", "B", 0): EdgeData(
                length_m=100.0,
                speed_kph=30.0,
                n_cells=20,
                vmax_cells=2,
                geometry_points=[(-99.15, 19.43), (-99.14, 19.43)],
            ),
            ("B", "C", 0): EdgeData(
                length_m=100.0,
                speed_kph=30.0,
                n_cells=20,
                vmax_cells=2,
                geometry_points=[(-99.14, 19.43), (-99.14, 19.44)],
            ),
        },
        bbox=BoundingBox(min_x=-99.15, max_x=-99.14, min_y=19.43, max_y=19.44),
    )

    model = NaSchSimulationModel(seed=7)
    initial_state = model.reset(
        topology,
        {
            "initial_vehicles": 0,
            "max_vehicles": 0,
            "spawn_rate": 0.0,
        },
    )

    assert initial_state.tick == 0
    assert initial_state.total_vehicles == 0

    new_state, metrics, done = model.step()

    assert new_state.tick == 1
    assert metrics.tick == 1
    assert metrics.total_vehicles == 0
    assert 0.0 <= metrics.density <= 1.0
    assert done is False
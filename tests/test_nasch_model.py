from traffic_engine.domain.models import BoundingBox, EdgeData, NodeData, SimulationConfig, TopologyData
from traffic_engine.domain.simulation import NaSchSimulationModel


def test_nasch_model_reset_and_step_returns_state_and_metrics() -> None:
    topology = TopologyData(
        nodes={
            "A": NodeData(x=-99.15, y=19.43, is_boundary=True),
            "B": NodeData(x=-99.14, y=19.43, is_boundary=False),
            "C": NodeData(x=-99.13, y=19.43, is_boundary=True),
        },
        edges={
            (
                "A",
                "B",
                0,
            ): EdgeData(
                length_m=75.0,
                speed_kph=30.0,
                travel_time_sec=9.0,
                n_cells=10,
                vmax_cells=2,
                geometry_points=[(-99.15, 19.43), (-99.14, 19.43)],
            ),
            (
                "B",
                "C",
                0,
            ): EdgeData(
                length_m=75.0,
                speed_kph=30.0,
                travel_time_sec=9.0,
                n_cells=10,
                vmax_cells=2,
                geometry_points=[(-99.14, 19.43), (-99.13, 19.43)],
            ),
        },
        bbox=BoundingBox(min_x=-99.15, max_x=-99.13, min_y=19.43, max_y=19.43),
    )

    model = NaSchSimulationModel(seed=7)
    initial_state = model.reset(
        topology=topology,
        config=SimulationConfig(
            initial_vehicles=1,
            max_vehicles=2,
            max_steps=3,
            spawn_rate=0.0,
            noise_prob=0.0,
            seed=7,
            tick_interval_ms=0,
        ),
    )

    state, metrics, done = model.step()

    assert initial_state.total_vehicles == 1
    assert state.step_number == 1
    assert metrics.step_number == 1
    assert 0.0 <= metrics.density <= 1.0
    assert done is False

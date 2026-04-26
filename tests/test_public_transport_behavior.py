"""Contract tests for public transport stop-and-dwell behavior."""

from __future__ import annotations

import importlib
import inspect
from typing import Any, Dict, Sequence

import numpy as np
import pytest


def _load_vehicle_symbols() -> Sequence[Any]:
    """Load PublicTransport and VehicleType symbols for TDD-first checks."""
    module_name = "traffic_engine.domain.models.vehicles"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        pytest.fail(f"Missing vehicles module '{module_name}': {exc}")

    if not hasattr(module, "PublicTransport"):
        pytest.fail("Missing 'PublicTransport' class in traffic_engine.domain.models.vehicles.")
    if not hasattr(module, "VehicleType"):
        pytest.fail("Missing 'VehicleType' enum in traffic_engine.domain.models.vehicles.")

    return getattr(module, "PublicTransport"), getattr(module, "VehicleType")


def _instantiate_public_transport(
    public_transport_cls: Any,
    vehicle_type: Any,
    **overrides: Any,
) -> Any:
    """Instantiate a PublicTransport object while remaining signature-compatible."""
    signature = inspect.signature(public_transport_cls)
    candidate_kwargs: Dict[str, Any] = {
        "vid": 700,
        "vtype": vehicle_type.BUS,
        "route": [("A", "B", 0), ("B", "C", 0)],
        "noise_prob": 0.1,
        "vmax_factor": 1.0,
        "edge_idx": 0,
        "cell_pos": 0,
        "velocity": 0,
        "station_node_ids": ["B", "C"],
        "current_station_idx": 0,
        "is_dwelling": False,
        "dwell_ticks_remaining": 0,
        "render_label": "BUS",
        "render_color": "#f39c12",
    }
    candidate_kwargs.update(overrides)

    accepted_kwargs = {
        name: candidate_kwargs[name]
        for name in signature.parameters
        if name in candidate_kwargs
    }
    missing_required = [
        name
        for name, parameter in signature.parameters.items()
        if parameter.default is inspect.Parameter.empty and name not in accepted_kwargs
    ]
    if missing_required:
        pytest.fail(
            "PublicTransport constructor has unsupported required parameters: "
            f"{missing_required}"
        )

    return public_transport_cls(**accepted_kwargs)


def _resolve_method(target: Any, method_names: Sequence[str]) -> Any:
    """Resolve the first available method name on a target object."""
    for method_name in method_names:
        if hasattr(target, method_name):
            return getattr(target, method_name)
    pytest.fail(f"Expected one of methods {list(method_names)} on {type(target).__name__}.")


def _invoke_with_supported_kwargs(callable_obj: Any, **kwargs: Any) -> Any:
    """Invoke callable with only supported keyword arguments."""
    signature = inspect.signature(callable_obj)
    accepted_kwargs = {
        name: kwargs[name]
        for name in signature.parameters
        if name in kwargs
    }
    return callable_obj(**accepted_kwargs)


class TestPublicTransportBehavior:
    """Test-first contracts for bus stops, dwell timing, and rendering metadata."""

    def test_public_transport_when_created_exposes_bus_render_metadata(self) -> None:
        """BUS entities should carry stable rendering metadata for visualization."""
        # Arrange
        public_transport_cls, vehicle_type = _load_vehicle_symbols()

        # Act
        bus = _instantiate_public_transport(public_transport_cls, vehicle_type)

        # Assert
        assert (
            getattr(bus, "render_label", None),
            bool(getattr(bus, "render_color", "")),
        ) == ("BUS", True)

    def test_public_transport_when_created_requires_station_node_ids_attribute(self) -> None:
        """Public transport entities should expose explicit station plans."""
        # Arrange
        public_transport_cls, vehicle_type = _load_vehicle_symbols()

        # Act
        bus = _instantiate_public_transport(public_transport_cls, vehicle_type)

        # Assert
        assert getattr(bus, "station_node_ids", None) == ["B", "C"]

    def test_public_transport_when_dwell_is_started_with_seeded_rng_is_deterministic_and_bounded(
        self,
    ) -> None:
        """Dwell duration should be reproducible under an injected RNG and stay in [10, 20]."""
        # Arrange
        public_transport_cls, vehicle_type = _load_vehicle_symbols()
        bus_a = _instantiate_public_transport(public_transport_cls, vehicle_type)
        bus_b = _instantiate_public_transport(public_transport_cls, vehicle_type)
        start_dwell_a = _resolve_method(
            bus_a,
            ("begin_station_dwell", "start_station_dwell", "start_dwell"),
        )
        start_dwell_b = _resolve_method(
            bus_b,
            ("begin_station_dwell", "start_station_dwell", "start_dwell"),
        )

        # Act
        _invoke_with_supported_kwargs(start_dwell_a, rng=np.random.default_rng(11))
        _invoke_with_supported_kwargs(start_dwell_b, rng=np.random.default_rng(11))
        dwell_a = int(getattr(bus_a, "dwell_ticks_remaining", -1))
        dwell_b = int(getattr(bus_b, "dwell_ticks_remaining", -1))

        # Assert
        assert (dwell_a, dwell_b, 10 <= dwell_a <= 20) == (dwell_a, dwell_a, True)

    def test_public_transport_when_dwell_starts_sets_dwelling_state_and_remaining_ticks(self) -> None:
        """Entering a station stop should toggle dwelling state and initialize countdown."""
        # Arrange
        public_transport_cls, vehicle_type = _load_vehicle_symbols()
        bus = _instantiate_public_transport(public_transport_cls, vehicle_type)
        start_dwell = _resolve_method(
            bus,
            ("begin_station_dwell", "start_station_dwell", "start_dwell"),
        )

        # Act
        _invoke_with_supported_kwargs(start_dwell, rng=np.random.default_rng(42))

        # Assert
        assert (
            bool(getattr(bus, "is_dwelling", False)),
            10 <= int(getattr(bus, "dwell_ticks_remaining", -1)) <= 20,
        ) == (True, True)

    def test_public_transport_when_station_list_is_empty_raises_value_error(self) -> None:
        """Transit entities should reject empty station plans to avoid undefined stop behavior."""
        # Arrange
        public_transport_cls, vehicle_type = _load_vehicle_symbols()

        # Act / Assert
        # ASSUMPTION: empty station lists are invalid for PublicTransport routes.
        with pytest.raises(ValueError):
            _instantiate_public_transport(
                public_transport_cls,
                vehicle_type,
                station_node_ids=[],
            )

    def test_public_transport_when_dwell_countdown_reaches_zero_resumes_motion_state(self) -> None:
        """After dwell countdown reaches zero, buses should leave dwelling mode."""
        # Arrange
        public_transport_cls, vehicle_type = _load_vehicle_symbols()
        bus = _instantiate_public_transport(
            public_transport_cls,
            vehicle_type,
            is_dwelling=True,
            dwell_ticks_remaining=1,
        )
        tick_dwell = _resolve_method(
            bus,
            ("tick_station_dwell", "update_station_dwell", "step_dwell"),
        )

        # Act
        _invoke_with_supported_kwargs(tick_dwell)

        # Assert
        assert (
            bool(getattr(bus, "is_dwelling", True)),
            int(getattr(bus, "dwell_ticks_remaining", -1)),
        ) == (False, 0)
"""Contract tests for multilane extraction in topology conversion."""

from __future__ import annotations

import importlib
from typing import Any

import networkx as nx
import pytest


def _load_symbol(module_name: str, symbol_name: str) -> Any:
    """Load a symbol and fail fast with a focused TDD message."""
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        pytest.fail(f"Missing module '{module_name}' required by multilane conversion tests: {exc}")

    if not hasattr(module, symbol_name):
        pytest.fail(f"Missing symbol '{symbol_name}' in module '{module_name}'.")

    return getattr(module, symbol_name)


@pytest.fixture
def multilane_graph() -> nx.MultiDiGraph:
    """Build a deterministic graph containing multiple lane metadata formats."""
    graph = nx.MultiDiGraph()
    graph.add_node("A", x=-99.1332, y=19.4326)
    graph.add_node("B", x=-99.1322, y=19.4326)
    graph.add_node("C", x=-99.1322, y=19.4316)
    graph.add_node("D", x=-99.1332, y=19.4316)

    graph.add_edge(
        "A",
        "B",
        length=120.0,
        speed_kph=50.0,
        highway="primary",
        lanes="3",
    )
    graph.add_edge(
        "B",
        "C",
        length=100.0,
        speed_kph=40.0,
        highway="secondary",
    )
    graph.add_edge(
        "C",
        "D",
        length=110.0,
        speed_kph=45.0,
        highway="trunk",
        lanes=["2", "3"],
    )
    graph.add_edge(
        "D",
        "A",
        length=90.0,
        speed_kph=30.0,
        highway="service",
        lanes="unknown",
    )
    graph.add_edge(
        "A",
        "C",
        length=140.0,
        speed_kph=60.0,
        highway="motorway",
        lanes=4,
    )
    graph.add_edge(
        "B",
        "D",
        length=130.0,
        speed_kph=35.0,
        highway="residential",
        lanes="0",
    )
    return graph


class TestMultilaneTopologyConverter:
    """Test-first contracts for lane extraction and defaults in conversion."""

    def test_convert_graph_when_explicit_lanes_attribute_present_sets_edge_n_lanes(
        self,
        multilane_graph: nx.MultiDiGraph,
    ) -> None:
        """Explicit OSM lane metadata should map directly to edge lane count."""
        # Arrange
        converter_cls = _load_symbol(
            "traffic_engine.infrastructure.topology.topology_converter",
            "TopologyConverter",
        )
        converter = converter_cls()

        # Act
        topology = converter.convert_graph(multilane_graph)
        n_lanes = getattr(topology.edges[("A", "B", 0)], "n_lanes", None)

        # Assert
        assert n_lanes == 3

    def test_convert_graph_when_lanes_attribute_missing_uses_highway_default_n_lanes(
        self,
        multilane_graph: nx.MultiDiGraph,
    ) -> None:
        """Missing lane metadata should use deterministic defaults by highway type."""
        # Arrange
        converter_cls = _load_symbol(
            "traffic_engine.infrastructure.topology.topology_converter",
            "TopologyConverter",
        )
        converter = converter_cls()

        # Act
        topology = converter.convert_graph(multilane_graph)
        n_lanes = getattr(topology.edges[("B", "C", 0)], "n_lanes", None)

        # Assert
        assert n_lanes == 2

    def test_convert_graph_when_lanes_attribute_is_list_uses_first_parseable_value(
        self,
        multilane_graph: nx.MultiDiGraph,
    ) -> None:
        """List-valued lane metadata should support OSM variants without ambiguity."""
        # Arrange
        converter_cls = _load_symbol(
            "traffic_engine.infrastructure.topology.topology_converter",
            "TopologyConverter",
        )
        converter = converter_cls()

        # Act
        topology = converter.convert_graph(multilane_graph)
        n_lanes = getattr(topology.edges[("C", "D", 0)], "n_lanes", None)

        # Assert
        assert n_lanes == 2

    def test_convert_graph_when_lanes_attribute_is_numeric_uses_that_lane_count(
        self,
        multilane_graph: nx.MultiDiGraph,
    ) -> None:
        """Numeric lane values should map directly without string-only assumptions."""
        # Arrange
        converter_cls = _load_symbol(
            "traffic_engine.infrastructure.topology.topology_converter",
            "TopologyConverter",
        )
        converter = converter_cls()

        # Act
        topology = converter.convert_graph(multilane_graph)
        n_lanes = getattr(topology.edges[("A", "C", 0)], "n_lanes", None)

        # Assert
        assert n_lanes == 4

    def test_convert_graph_when_lanes_attribute_is_invalid_uses_single_lane_fallback(
        self,
        multilane_graph: nx.MultiDiGraph,
    ) -> None:
        """Unparseable lane metadata should fall back to one lane, never zero."""
        # Arrange
        converter_cls = _load_symbol(
            "traffic_engine.infrastructure.topology.topology_converter",
            "TopologyConverter",
        )
        converter = converter_cls()

        # Act
        topology = converter.convert_graph(multilane_graph)
        n_lanes = getattr(topology.edges[("D", "A", 0)], "n_lanes", None)

        # Assert
        assert n_lanes == 1

    def test_convert_graph_when_lanes_attribute_is_zero_clamps_to_at_least_one_lane(
        self,
        multilane_graph: nx.MultiDiGraph,
    ) -> None:
        """Lane counts should never fall below one, even for malformed zero values."""
        # Arrange
        converter_cls = _load_symbol(
            "traffic_engine.infrastructure.topology.topology_converter",
            "TopologyConverter",
        )
        converter = converter_cls()

        # Act
        topology = converter.convert_graph(multilane_graph)
        n_lanes = getattr(topology.edges[("B", "D", 0)], "n_lanes", None)

        # Assert
        assert n_lanes == 1

    def test_convert_graph_when_input_is_not_multidigraph_raises_value_error(self) -> None:
        """Converter should reject unsupported graph types with an explicit error."""
        # Arrange
        converter_cls = _load_symbol(
            "traffic_engine.infrastructure.topology.topology_converter",
            "TopologyConverter",
        )
        converter = converter_cls()

        # Act / Assert
        with pytest.raises(ValueError):
            converter.convert_graph({"nodes": [], "edges": []})
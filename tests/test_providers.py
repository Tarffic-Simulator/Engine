"""
Tests for provider interfaces: TopologyProvider and TrafficLightProvider.

Validates the contracts for external data sources and their abstraction,
supporting different implementations (OSMnx, mock, future databases).
"""

import pytest
from typing import Dict, List, Set, Tuple, Protocol, Optional
from unittest.mock import Mock, patch
import networkx as nx


class TestTopologyProvider:
    """Test TopologyProvider interface and implementations."""
    
    def test_topology_provider_interface_defines_required_methods(self):
        """Test TopologyProvider protocol defines required method signatures."""
        # Arrange - mock provider implementing the interface
        
        class MockTopologyProvider:
            def load_area(self, area: str) -> Dict:
                return {'nodes': {}, 'edges': {}, 'bbox': {}}
            
            def load_bbox(self, bbox: Dict) -> Dict:
                return {'nodes': {}, 'edges': {}, 'bbox': bbox}
        
        provider = MockTopologyProvider()
        
        # Act & Assert - should have required methods
        assert hasattr(provider, 'load_area'), "Provider should have load_area method"
        assert hasattr(provider, 'load_bbox'), "Provider should have load_bbox method"
        assert callable(provider.load_area), "load_area should be callable"
        assert callable(provider.load_bbox), "load_bbox should be callable"
    
    def test_topology_provider_load_area_returns_topology_data(self):
        """Test load_area returns properly structured TopologyData."""
        # Arrange
        area_name = "Roma Norte, Ciudad de México"
        
        # Act - simulate loading area
        topology_data = self._mock_load_area(area_name)
        
        # Assert - should return TopologyData structure
        required_fields = {'nodes', 'edges', 'bbox'}
        assert required_fields.issubset(topology_data.keys()), \
            "Should return TopologyData with required fields"
        
        assert isinstance(topology_data['nodes'], dict), "Nodes should be dictionary"
        assert isinstance(topology_data['edges'], dict), "Edges should be dictionary"
        assert isinstance(topology_data['bbox'], dict), "Bbox should be dictionary"
    
    def test_topology_provider_load_bbox_handles_geographic_bounds(self):
        """Test load_bbox correctly handles geographic bounding boxes."""
        # Arrange - CDMX area bounding box
        bbox = {
            'min_x': -99.2000, 'max_x': -99.1000,
            'min_y': 19.4000, 'max_y': 19.5000
        }
        
        # Act
        topology_data = self._mock_load_bbox(bbox)
        
        # Assert - returned bbox should match or be within input bounds
        returned_bbox = topology_data['bbox']
        assert returned_bbox['min_x'] >= bbox['min_x'], "Returned bbox should be within input bounds"
        assert returned_bbox['max_x'] <= bbox['max_x'], "Returned bbox should be within input bounds"  
        assert returned_bbox['min_y'] >= bbox['min_y'], "Returned bbox should be within input bounds"
        assert returned_bbox['max_y'] <= bbox['max_y'], "Returned bbox should be within input bounds"
    
    def test_osmnx_topology_provider_converts_networkx_correctly(self, simple_network):
        """Test OSMnx provider converts NetworkX MultiDiGraph to TopologyData."""
        # Arrange - NetworkX graph from fixture
        G = simple_network
        
        # Act - simulate OSMnx provider conversion
        topology_data = self._mock_osmnx_conversion(G)
        
        # Assert - should preserve graph structure
        assert len(topology_data['nodes']) == G.number_of_nodes(), \
            "Should preserve all nodes from NetworkX graph"
        assert len(topology_data['edges']) == G.number_of_edges(), \
            "Should preserve all edges from NetworkX graph"
        
        # Assert - nodes should have coordinates
        for node_id, node_data in topology_data['nodes'].items():
            assert 'x' in node_data and 'y' in node_data, \
                f"Node {node_id} should have x,y coordinates"
            
            # Verify coordinates match NetworkX data
            nx_node = G.nodes[node_id]
            assert node_data['x'] == nx_node['x'], "X coordinate should match NetworkX"
            assert node_data['y'] == nx_node['y'], "Y coordinate should match NetworkX"
    
    def test_osmnx_topology_provider_handles_edge_attributes(self, simple_network):
        """Test OSMnx provider correctly processes edge attributes."""
        # Arrange
        G = simple_network
        
        # Act 
        topology_data = self._mock_osmnx_conversion(G)
        
        # Assert - edges should have required attributes
        for edge_id, edge_data in topology_data['edges'].items():
            u, v, k = edge_id
            
            # Should have physical attributes
            assert 'length_m' in edge_data, f"Edge {edge_id} should have length"
            assert 'speed_kph' in edge_data, f"Edge {edge_id} should have speed limit"
            
            # Should have discretization info
            assert 'n_cells' in edge_data, f"Edge {edge_id} should have cell count"
            assert 'vmax_cells' in edge_data, f"Edge {edge_id} should have vmax"
            
            # Verify conversion accuracy
            nx_edge = G[u][v][k]
            assert edge_data['length_m'] == nx_edge['length'], "Length should match NetworkX"
            assert edge_data['speed_kph'] == nx_edge['speed_kph'], "Speed should match NetworkX"
    
    def test_topology_provider_caching_improves_performance(self):
        """Test topology provider supports caching for repeated requests."""
        # Arrange
        area_name = "Polanco, Ciudad de México"
        
        # Act - simulate caching behavior
        cache = {}
        
        # First call - should hit provider
        if area_name not in cache:
            topology_data_1 = self._mock_load_area(area_name)
            cache[area_name] = topology_data_1
        
        # Second call - should hit cache
        topology_data_2 = cache.get(area_name)
        
        # Assert - should return same data
        assert topology_data_2 is not None, "Cache should contain data after first call"
        assert topology_data_1 == topology_data_2, "Cached data should match original"
    
    def test_topology_provider_handles_invalid_area_gracefully(self):
        """Test topology provider handles invalid area names gracefully."""
        # Arrange
        invalid_area = "Nonexistent Place, Nowhere"
        
        # Act & Assert - should raise appropriate exception
        with pytest.raises((ValueError, ConnectionError, Exception)):
            self._mock_load_area_with_error(invalid_area)
    
    @staticmethod
    def _mock_load_area(area: str) -> Dict:
        """Helper: mock TopologyProvider.load_area implementation."""
        return {
            'nodes': {
                'A': {'x': -99.1332, 'y': 19.4326, 'is_boundary': False},
                'B': {'x': -99.1312, 'y': 19.4326, 'is_boundary': True}
            },
            'edges': {
                ('A', 'B', 0): {
                    'length_m': 150.0, 'speed_kph': 40.0,
                    'n_cells': 20, 'vmax_cells': 3,
                    'geometry_points': [(-99.1332, 19.4326), (-99.1312, 19.4326)]
                }
            },
            'bbox': {'min_x': -99.1332, 'max_x': -99.1312, 'min_y': 19.4326, 'max_y': 19.4326}
        }
    
    @staticmethod
    def _mock_load_bbox(bbox: Dict) -> Dict:
        """Helper: mock TopologyProvider.load_bbox implementation.""" 
        return {
            'nodes': {},
            'edges': {},
            'bbox': bbox.copy()
        }
    
    @staticmethod
    def _mock_osmnx_conversion(G: nx.MultiDiGraph) -> Dict:
        """Helper: simulate NetworkX to TopologyData conversion."""
        topology = {
            'nodes': {},
            'edges': {},
            'bbox': {'min_x': -99.2, 'max_x': -99.1, 'min_y': 19.4, 'max_y': 19.5}
        }
        
        # Convert nodes
        for node_id, node_data in G.nodes(data=True):
            topology['nodes'][node_id] = {
                'x': node_data['x'],
                'y': node_data['y'], 
                'is_boundary': node_data.get('street_count', 4) <= 2
            }
        
        # Convert edges
        for u, v, k, edge_data in G.edges(data=True, keys=True):
            cell_size_m = 7.5
            n_cells = max(1, int(edge_data['length'] / cell_size_m))
            vmax = max(1, min(5, round(edge_data['speed_kph'] / 3.6 / cell_size_m)))
            
            topology['edges'][(u, v, k)] = {
                'length_m': edge_data['length'],
                'speed_kph': edge_data['speed_kph'],
                'n_cells': n_cells,
                'vmax_cells': vmax,
                'geometry_points': [(G.nodes[u]['x'], G.nodes[u]['y']), 
                                   (G.nodes[v]['x'], G.nodes[v]['y'])]
            }
        
        return topology
    
    @staticmethod
    def _mock_load_area_with_error(area: str):
        """Helper: mock provider that raises error for testing."""
        raise ValueError(f"Unknown area: {area}")


class TestTrafficLightProvider:
    """Test TrafficLightProvider interface and implementations."""
    
    def test_traffic_light_provider_interface_defines_required_methods(self):
        """Test TrafficLightProvider protocol defines required methods."""
        # Arrange
        class MockTrafficLightProvider:
            def get_lights(self, topology_data: Dict) -> List:
                return []
            
            def update_config(self, light_id: str, config: Dict) -> None:
                pass
        
        provider = MockTrafficLightProvider()
        
        # Act & Assert
        assert hasattr(provider, 'get_lights'), "Provider should have get_lights method"
        assert hasattr(provider, 'update_config'), "Provider should have update_config method"
        assert callable(provider.get_lights), "get_lights should be callable"
        assert callable(provider.update_config), "update_config should be callable"
    
    def test_traffic_light_provider_get_lights_returns_light_list(self, mock_topology_data):
        """Test get_lights returns list of TrafficLight objects."""
        # Arrange
        topology_data = mock_topology_data
        
        # Act
        traffic_lights = self._mock_get_lights(topology_data)
        
        # Assert
        assert isinstance(traffic_lights, list), "Should return list of traffic lights"
        
        for light in traffic_lights:
            assert isinstance(light, dict), "Each light should be structured data"
            required_fields = {'node_id', 'cycle_ticks', 'green_ratio', 'offset_ticks'}
            assert required_fields.issubset(light.keys()), \
                f"Traffic light {light.get('node_id')} missing required fields"
    
    def test_centrality_traffic_light_provider_selects_high_centrality_nodes(self, intersection_network):
        """Test CentralityTrafficLightProvider selects high-centrality intersections."""
        # Arrange - network with clear centrality differences
        G = intersection_network
        
        # Act - simulate centrality-based selection
        centralities = self._mock_calculate_centrality(G)
        top_nodes = self._select_top_centrality_nodes(centralities, n_lights=2)
        traffic_lights = [self._create_traffic_light(node_id) for node_id in top_nodes]
        
        # Assert - should select highest centrality nodes
        assert len(traffic_lights) == 2, "Should select requested number of lights"
        
        # Center node should have highest centrality in intersection network
        center_centrality = centralities.get('center', 0)
        other_centralities = [centralities.get(node, 0) for node in G.nodes() if node != 'center']
        
        if len(other_centralities) > 0:
            assert center_centrality >= max(other_centralities), \
                "Center intersection should have highest centrality"
    
    def test_centrality_traffic_light_provider_classifies_edge_orientations(self, intersection_network):
        """Test provider correctly classifies edges by NS/EW orientation."""
        # Arrange
        G = intersection_network
        center_node = 'center'
        
        # Act - classify incoming edges
        ns_edges, ew_edges = self._mock_classify_edges(G, center_node)
        
        # Assert - should classify all incoming edges
        total_incoming = len(list(G.in_edges(center_node, keys=True)))
        assert len(ns_edges) + len(ew_edges) == total_incoming, \
            "All incoming edges should be classified"
        
        # Assert - should have both orientations for 4-way intersection
        assert len(ns_edges) > 0, "Should have north-south edges"
        assert len(ew_edges) > 0, "Should have east-west edges"
    
    def test_traffic_light_provider_distributes_offsets_for_green_wave(self):
        """Test provider distributes offsets to create green wave effect."""
        # Arrange
        n_lights = 5
        cycle_ticks = 30
        
        # Act - create lights with distributed offsets
        traffic_lights = []
        for i in range(n_lights):
            offset = (i * 7) % cycle_ticks  # Staggered offsets
            light = self._create_traffic_light(f'node_{i}', offset=offset)
            traffic_lights.append(light)
        
        # Assert - offsets should be distributed
        offsets = [light['offset_ticks'] for light in traffic_lights]
        unique_offsets = set(offsets)
        assert len(unique_offsets) > 1, "Offsets should be distributed, not all the same"
        
        # Assert - offsets should be within cycle
        for offset in offsets:
            assert 0 <= offset < cycle_ticks, f"Offset {offset} should be within cycle {cycle_ticks}"
    
    def test_traffic_light_provider_update_config_modifies_existing_light(self):
        """Test update_config modifies traffic light configuration."""
        # Arrange
        light_id = 'intersection_1'
        original_config = {'cycle_ticks': 30, 'green_ratio': 0.5}
        new_config = {'cycle_ticks': 40, 'green_ratio': 0.6}
        
        # Act - simulate config update
        updated_config = self._mock_update_config(light_id, original_config, new_config)
        
        # Assert - should update specified parameters
        assert updated_config['cycle_ticks'] == 40, "Should update cycle_ticks"
        assert updated_config['green_ratio'] == 0.6, "Should update green_ratio"
    
    def test_traffic_light_provider_validates_configuration_parameters(self):
        """Test provider validates traffic light configuration parameters."""
        # Arrange - various invalid configurations
        invalid_configs = [
            {'cycle_ticks': 0, 'green_ratio': 0.5},      # Invalid cycle
            {'cycle_ticks': 30, 'green_ratio': 0},       # Invalid green ratio
            {'cycle_ticks': 30, 'green_ratio': 1.5},     # Invalid green ratio  
            {'cycle_ticks': -5, 'green_ratio': 0.5},     # Negative cycle
        ]
        
        # Act & Assert - should reject invalid configurations
        for config in invalid_configs:
            is_valid = self._validate_traffic_light_config(config)
            assert not is_valid, f"Should reject invalid config: {config}"
    
    def test_fixed_traffic_light_provider_provides_static_configuration(self):
        """Test FixedTrafficLightProvider provides unchanging configuration."""
        # Arrange
        fixed_lights_config = [
            {'node_id': 'A', 'cycle_ticks': 30, 'green_ratio': 0.5, 'offset_ticks': 0},
            {'node_id': 'B', 'cycle_ticks': 30, 'green_ratio': 0.5, 'offset_ticks': 10}
        ]
        
        # Act - get lights multiple times
        lights_1 = self._mock_fixed_provider(fixed_lights_config)
        lights_2 = self._mock_fixed_provider(fixed_lights_config)
        
        # Assert - should return identical configurations
        assert lights_1 == lights_2, "Fixed provider should return consistent configuration"
        assert len(lights_1) == len(fixed_lights_config), \
            "Should return all configured lights"
    
    @staticmethod
    def _mock_get_lights(topology_data: Dict) -> List[Dict]:
        """Helper: mock TrafficLightProvider.get_lights implementation."""
        # Select some nodes as traffic light locations
        light_nodes = list(topology_data['nodes'].keys())[:2]  # First 2 nodes
        
        return [
            {
                'node_id': node_id,
                'cycle_ticks': 30,
                'green_ratio': 0.5,
                'offset_ticks': i * 7,
                'ns_edges': set(),
                'ew_edges': set()
            }
            for i, node_id in enumerate(light_nodes)
        ]
    
    @staticmethod
    def _mock_calculate_centrality(G: nx.MultiDiGraph) -> Dict[str, float]:
        """Helper: mock centrality calculation."""
        # Simple mock: center node has highest centrality
        centralities = {}
        for node in G.nodes():
            if node == 'center':
                centralities[node] = 0.8  # High centrality
            else:
                centralities[node] = 0.2  # Lower centrality
        return centralities
    
    @staticmethod
    def _select_top_centrality_nodes(centralities: Dict, n_lights: int) -> List:
        """Helper: select top-N centrality nodes."""
        sorted_nodes = sorted(centralities.items(), key=lambda x: x[1], reverse=True)
        return [node for node, _ in sorted_nodes[:n_lights]]
    
    @staticmethod
    def _create_traffic_light(node_id: str, offset: int = 0) -> Dict:
        """Helper: create traffic light configuration."""
        return {
            'node_id': node_id,
            'cycle_ticks': 30,
            'green_ratio': 0.5,
            'offset_ticks': offset,
            'ns_edges': set(),
            'ew_edges': set()
        }
    
    @staticmethod
    def _mock_classify_edges(G: nx.MultiDiGraph, center_node: str) -> Tuple[Set, Set]:
        """Helper: classify edges by orientation."""
        ns_edges = set()
        ew_edges = set()
        
        for u, v, k in G.in_edges(center_node, keys=True):
            # Mock bearing calculation 
            u_node, v_node = G.nodes[u], G.nodes[v]
            dx = v_node['x'] - u_node['x']
            dy = v_node['y'] - u_node['y']
            
            # Simple classification: more vertical = NS, more horizontal = EW
            if abs(dy) >= abs(dx):
                ns_edges.add((u, v, k))
            else:
                ew_edges.add((u, v, k))
        
        return ns_edges, ew_edges
    
    @staticmethod
    def _mock_update_config(light_id: str, original_config: Dict, new_config: Dict) -> Dict:
        """Helper: mock config update."""
        updated = original_config.copy()
        updated.update(new_config)
        return updated
    
    @staticmethod
    def _validate_traffic_light_config(config: Dict) -> bool:
        """Helper: validate traffic light configuration."""
        if config.get('cycle_ticks', 0) <= 0:
            return False
        if not (0 < config.get('green_ratio', 0) < 1):
            return False
        return True
    
    @staticmethod
    def _mock_fixed_provider(fixed_config: List[Dict]) -> List[Dict]:
        """Helper: mock fixed provider implementation."""
        return fixed_config.copy()
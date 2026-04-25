"""
NaSch simulation model implementation.

Implements the SimulationModel protocol with the synchronous NaSch cellular automata
algorithm, preserving the behavior from the prototype while providing a clean interface.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass

from .interfaces import SimulationModel
from .cellular_grid import CellularGrid
from .nasch_rules import apply_nasch_rules, speed_to_vmax
from ..models import (
    TopologyData, SimulationState, Metrics, SnapshotData, StepResult,
    Vehicle, VehicleState, VehicleType, VEHICLE_TYPE_CONFIGS,
    TrafficLight, LightState, calculate_bearing, is_ns_orientation,
    EdgeId, NodeId
)
from ...config.constants import (
    CELL_SIZE_M, TICK_SECONDS, NOISE_PROB, TIMEOUT_TICKS,
    ENTRY_PROB, EXIT_PROB, BOUNDARY_MARGIN, VEHICLE_TYPE_WEIGHTS,
    DEFAULT_CYCLE_TICKS, DEFAULT_GREEN_RATIO
)


class NaSchSimulationModel:
    """
    NaSch cellular automata simulation model.
    
    Implements the complete synchronous NaSch algorithm with:
    - Four-step synchronous updates (acceleration, braking, noise, movement)
    - Conflict resolution with guaranteed no overlap
    - Heterogeneous vehicle types and driver behavior  
    - Traffic light coordination with NS/EW phases
    - Boundary inflow/outflow management
    - Vehicle timeout and removal
    """
    
    def __init__(self, seed: int = 42):
        """
        Initialize NaSch simulation model.
        
        Args:
            seed: Random seed for reproducible simulations
        """
        self.rng = np.random.default_rng(seed)
        self.topology: Optional[TopologyData] = None
        self.grid: Optional[CellularGrid] = None
        self.vehicles: Dict[int, Vehicle] = {}
        self.traffic_lights: Dict[NodeId, TrafficLight] = {}
        self.boundary_nodes: Set[NodeId] = set()
        self.tick = 0
        self._next_vehicle_id = 1
        
        # Metrics tracking
        self.vehicles_spawned_this_tick = 0
        self.vehicles_removed_this_tick = 0
        self.total_vehicles_spawned = 0
        self.total_vehicles_removed = 0
        
        # Configuration
        self.config = {
            'noise_prob': NOISE_PROB,
            'timeout_ticks': TIMEOUT_TICKS,
            'entry_prob': ENTRY_PROB,
            'exit_prob': EXIT_PROB,
            'spawn_rate': 0.1,  # Vehicles per boundary node per tick
        }
    
    def reset(self, topology: TopologyData, config: Optional[Dict[str, Any]] = None) -> SimulationState:
        """Reset simulation with new topology and configuration."""
        self.topology = topology
        self.grid = CellularGrid(topology)
        self.vehicles.clear()
        self.traffic_lights.clear()
        self.boundary_nodes.clear()
        self.tick = 0
        self._next_vehicle_id = 1
        
        # Apply configuration overrides
        if config:
            self.config.update(config)
        
        # Identify boundary nodes
        self._identify_boundary_nodes()
        
        # Setup traffic lights (simplified version - can be overridden by providers)
        self._setup_basic_traffic_lights()
        
        # Spawn initial vehicles if requested
        initial_vehicles = self.config.get('initial_vehicles', 0)
        if initial_vehicles > 0:
            self._spawn_vehicles(initial_vehicles)
        
        return self._get_current_state()
    
    def step(self, actions: Optional[Dict[str, Any]] = None) -> Tuple[SimulationState, Metrics, bool]:
        """Advance simulation by one tick with synchronous NaSch algorithm."""
        self.vehicles_spawned_this_tick = 0
        self.vehicles_removed_this_tick = 0
        
        if not self.vehicles and not self._should_spawn_vehicles():
            # Empty simulation, just advance time
            self.tick += 1
            state = self._get_current_state()
            metrics = self._calculate_metrics()
            return state, metrics, False
        
        # Apply actions if provided
        if actions:
            self._apply_actions(actions)
        
        # Synchronous NaSch step
        self._step_nasch_synchronous()
        
        # Boundary management
        self._handle_boundary_flow()
        
        # Remove timed out vehicles
        self._remove_timed_out_vehicles()
        
        # Advance time
        self.tick += 1
        
        # Generate results
        state = self._get_current_state()
        metrics = self._calculate_metrics()
        done = self._check_termination()
        
        return state, metrics, done
    
    def get_observation(self) -> SnapshotData:
        """Get detailed simulation state for visualization."""
        vehicle_states = []
        for vehicle in self.vehicles.values():
            vehicle_states.append(self._vehicle_to_state(vehicle))
        
        light_states = []
        for light in self.traffic_lights.values():
            light_states.append(self._traffic_light_to_state(light))
        
        edge_densities = {}
        edge_flows = {}
        for edge_id in self.topology.edges:
            edge_densities[edge_id] = self.grid.get_edge_density(edge_id)
            edge_flows[edge_id] = self.grid.get_edge_flow(edge_id)
        
        return SnapshotData(
            tick=self.tick,
            vehicles=vehicle_states,
            traffic_lights=light_states,
            edge_densities=edge_densities,
            edge_flows=edge_flows,
            bbox={
                'min_x': self.topology.bbox.min_x,
                'max_x': self.topology.bbox.max_x,
                'min_y': self.topology.bbox.min_y,
                'max_y': self.topology.bbox.max_y,
            }
        )
    
    def get_current_tick(self) -> int:
        """Get current simulation time step."""
        return self.tick
    
    def get_vehicle_count(self) -> int:
        """Get current number of active vehicles."""
        return len(self.vehicles)
    
    def get_state(self) -> SimulationState:
        """Get current simulation state (public interface)."""
        return self._get_current_state()
    
    def get_metrics(self) -> Metrics:
        """Get current simulation metrics (public interface)."""
        return self._calculate_metrics()
    
    def add_traffic_light(self, light: TrafficLight):
        """Add traffic light to simulation."""
        self.traffic_lights[light.node_id] = light
    
    def _identify_boundary_nodes(self):
        """Identify boundary nodes based on geographic position."""
        if not self.topology:
            return
        
        bbox = self.topology.bbox
        x_range = bbox.max_x - bbox.min_x
        y_range = bbox.max_y - bbox.min_y
        x_margin = x_range * BOUNDARY_MARGIN
        y_margin = y_range * BOUNDARY_MARGIN
        
        for node_id, node_data in self.topology.nodes.items():
            if (node_data.x <= bbox.min_x + x_margin or 
                node_data.x >= bbox.max_x - x_margin or
                node_data.y <= bbox.min_y + y_margin or
                node_data.y >= bbox.max_y - y_margin):
                self.boundary_nodes.add(node_id)
        
        # Also use explicit boundary marking if available
        for node_id, node_data in self.topology.nodes.items():
            if node_data.is_boundary:
                self.boundary_nodes.add(node_id)
    
    def _setup_basic_traffic_lights(self):
        """Setup basic traffic lights at major intersections."""
        if not self.topology:
            return
        
        # Find nodes with high connectivity (simplified centrality)
        node_degrees = {}
        for edge_id in self.topology.edges:
            u, v, k = edge_id
            node_degrees[u] = node_degrees.get(u, 0) + 1
            node_degrees[v] = node_degrees.get(v, 0) + 1
        
        # Create lights at high-degree intersections
        high_degree_nodes = [node for node, degree in node_degrees.items() 
                           if degree >= 4 and node not in self.boundary_nodes]
        
        for i, node_id in enumerate(high_degree_nodes[:20]):  # Limit to 20 lights
            light = TrafficLight(
                node_id=node_id,
                cycle_ticks=DEFAULT_CYCLE_TICKS,
                green_ratio=DEFAULT_GREEN_RATIO,
                offset_ticks=(i * 7) % DEFAULT_CYCLE_TICKS  # Stagger offsets
            )
            
            # Classify edges by bearing
            self._classify_light_edges(light)
            self.traffic_lights[node_id] = light
    
    def _classify_light_edges(self, light: TrafficLight):
        """Classify incoming edges as NS or EW based on bearing."""
        node_id = light.node_id
        node_data = self.topology.nodes[node_id]
        
        for edge_id, edge_data in self.topology.edges.items():
            u, v, k = edge_id
            if v == node_id:  # Incoming edge
                u_data = self.topology.nodes[u]
                bearing = calculate_bearing(u_data.x, u_data.y, node_data.x, node_data.y)
                
                if is_ns_orientation(bearing):
                    light.ns_edges.add(edge_id)
                else:
                    light.ew_edges.add(edge_id)
    
    def _step_nasch_synchronous(self):
        """Execute synchronous NaSch algorithm."""
        if not self.vehicles:
            return
        
        # Phase 1: Calculate new velocities using current state snapshot
        new_velocities = {}
        for vid, vehicle in self.vehicles.items():
            # Check traffic light
            dest_node = vehicle.current_edge[1]
            light_green = True
            if dest_node in self.traffic_lights:
                light = self.traffic_lights[dest_node]
                light_green = light.is_green(vehicle.current_edge, self.tick)
            
            # Apply NaSch rules
            new_velocity = apply_nasch_rules(
                vehicle, 
                self.grid.edge_cells,
                self._get_edge_vmax_dict(),
                light_green,
                self.rng
            )
            new_velocities[vid] = new_velocity
        
        # Phase 2: Clear all old positions
        for vehicle in self.vehicles.values():
            self.grid.remove_vehicle(vehicle.current_edge, vehicle.cell_pos)
        
        # Phase 3: Calculate new positions and handle conflicts
        new_positions = {}
        removed_vehicles = []
        
        # Sort vehicles by velocity (highest first) for conflict resolution
        sorted_vehicles = sorted(self.vehicles.items(), key=lambda x: -new_velocities[x[0]])
        
        for vid, vehicle in sorted_vehicles:
            new_vel = new_velocities[vid]
            if new_vel == 0:
                # No movement
                new_positions[vid] = (vehicle.edge_idx, vehicle.cell_pos, new_vel)
                continue
            
            # Calculate candidate position
            new_edge_idx, new_pos = self._calculate_new_position(vehicle, new_vel)
            
            # Check if reached destination
            if new_edge_idx >= len(vehicle.route):
                removed_vehicles.append(vid)
                continue
            
            new_edge_id = vehicle.route[new_edge_idx]
            edge_length = self.grid.get_edge_length(new_edge_id)
            new_pos = min(new_pos, edge_length - 1)
            
            new_positions[vid] = (new_edge_idx, new_pos, new_vel)
        
        # Phase 4: Apply movements with conflict resolution
        claimed_cells = {}
        
        for vid, vehicle in sorted_vehicles:
            if vid in removed_vehicles:
                continue
            
            new_edge_idx, new_pos, new_vel = new_positions[vid]
            new_edge_id = vehicle.route[new_edge_idx]
            original_edge_idx = vehicle.edge_idx
            original_cell_pos = vehicle.cell_pos
            original_edge_id = vehicle.current_edge
            
            # Check for conflict
            if new_edge_id not in claimed_cells:
                claimed_cells[new_edge_id] = set()
            
            if new_pos in claimed_cells[new_edge_id]:
                # Conflict - find alternative position or revert
                placed = False
                
                # Try positions behind the desired one
                for fallback_pos in range(new_pos - 1, max(-1, original_cell_pos), -1):
                    if fallback_pos not in claimed_cells[new_edge_id]:
                        vehicle.edge_idx = new_edge_idx
                        vehicle.cell_pos = fallback_pos
                        if new_edge_idx == original_edge_idx:
                            vehicle.velocity = max(0, fallback_pos - original_cell_pos)
                        else:
                            vehicle.velocity = 0
                        claimed_cells[new_edge_id].add(fallback_pos)
                        placed = True
                        break
                
                if not placed:
                    # Revert to original position
                    vehicle.edge_idx = original_edge_idx
                    vehicle.cell_pos = original_cell_pos
                    if original_edge_id not in claimed_cells:
                        claimed_cells[original_edge_id] = set()
                    claimed_cells[original_edge_id].add(original_cell_pos)
                    vehicle.velocity = 0
            else:
                # No conflict - apply movement
                vehicle.edge_idx = new_edge_idx
                vehicle.cell_pos = new_pos
                vehicle.velocity = new_vel
                claimed_cells[new_edge_id].add(new_pos)
            
            # Update wait ticks
            if vehicle.velocity == 0:
                vehicle.wait_ticks += 1
            else:
                vehicle.wait_ticks = 0
            
            # Update distance traveled
            vehicle.distance_traveled_m += vehicle.velocity * CELL_SIZE_M
            
            # Place vehicle in grid
            self.grid.place_vehicle(vehicle.current_edge, vehicle.cell_pos, vid)
        
        # Remove vehicles that reached destination
        for vid in removed_vehicles:
            del self.vehicles[vid]
            self.vehicles_removed_this_tick += 1
    
    def _calculate_new_position(self, vehicle: Vehicle, velocity: int) -> Tuple[int, int]:
        """Calculate new edge and position after movement."""
        new_edge_idx = vehicle.edge_idx
        new_pos = vehicle.cell_pos + velocity
        
        # Handle edge transitions
        while new_edge_idx < len(vehicle.route):
            edge_id = vehicle.route[new_edge_idx]
            edge_length = self.grid.get_edge_length(edge_id)
            
            if new_pos < edge_length:
                break
            
            new_pos -= edge_length
            new_edge_idx += 1
        
        return new_edge_idx, new_pos
    
    def _get_edge_vmax_dict(self) -> Dict[EdgeId, int]:
        """Get vmax values for all edges."""
        edge_vmax = {}
        for edge_id, edge_data in self.topology.edges.items():
            edge_vmax[edge_id] = speed_to_vmax(edge_data.speed_kph)
        return edge_vmax
    
    def _handle_boundary_flow(self):
        """Handle vehicle spawning at boundary nodes."""
        if not self._should_spawn_vehicles():
            return
        
        boundary_nodes_list = list(self.boundary_nodes)
        if not boundary_nodes_list:
            return
        
        spawn_rate = self.config.get('spawn_rate', 0.1)
        
        for _ in range(int(len(boundary_nodes_list) * spawn_rate) + 1):
            if self.rng.random() < spawn_rate:
                self._spawn_single_vehicle()
    
    def _should_spawn_vehicles(self) -> bool:
        """Check if vehicles should be spawned this tick."""
        max_vehicles = self.config.get('max_vehicles', 1000)
        return len(self.vehicles) < max_vehicles
    
    def _spawn_single_vehicle(self) -> bool:
        """Spawn a single vehicle with random route."""
        route = self._generate_random_route()
        if not route:
            return False
        
        # Find spawn position
        first_edge = route[0]
        free_cells = self.grid.find_free_cells(first_edge, 5)
        if not free_cells:
            return False
        
        # Choose vehicle type
        vtype = self.rng.choice(list(VehicleType), p=VEHICLE_TYPE_WEIGHTS)
        config = VEHICLE_TYPE_CONFIGS[vtype]
        
        # Generate heterogeneous driver parameters
        noise_prob = np.clip(
            self.rng.normal(NOISE_PROB * config.noise_factor, 0.08), 
            0.05, 0.7
        )
        vmax_factor = np.clip(self.rng.normal(1.0, 0.12), 0.7, 1.3)
        
        # Create vehicle
        vid = self._next_vehicle_id
        self._next_vehicle_id += 1
        
        vehicle = Vehicle(
            vid=vid,
            vtype=vtype,
            route=route,
            noise_prob=noise_prob,
            vmax_factor=vmax_factor,
            cell_pos=free_cells[0]
        )
        
        self.vehicles[vid] = vehicle
        self.grid.place_vehicle(first_edge, free_cells[0], vid)
        self.vehicles_spawned_this_tick += 1
        return True
    
    def _spawn_vehicles(self, count: int) -> int:
        """Spawn multiple vehicles."""
        spawned = 0
        for _ in range(count * 3):  # Try up to 3x to handle failures
            if spawned >= count:
                break
            if self._spawn_single_vehicle():
                spawned += 1
        return spawned
    
    def _generate_random_route(self) -> Optional[List[EdgeId]]:
        """Generate random route between nodes.""" 
        # Simplified route generation - would use proper pathfinding in production
        all_edges = list(self.topology.edges.keys())
        if len(all_edges) < 2:
            return None
        
        # Select random start and end edges
        start_edge = all_edges[int(self.rng.integers(0, len(all_edges)))]
        
        # Build simple route of 3-8 connected edges
        route = [start_edge]
        current_node = start_edge[1]
        
        for _ in range(self.rng.integers(2, 8)):
            # Find edges starting from current node
            outgoing = [eid for eid in all_edges if eid[0] == current_node]
            if not outgoing:
                break
            
            next_edge = outgoing[int(self.rng.integers(0, len(outgoing)))]
            route.append(next_edge)
            current_node = next_edge[1]
        
        return route if len(route) >= 2 else None
    
    def _remove_timed_out_vehicles(self):
        """Remove vehicles that have been stationary too long."""
        timeout_limit = self.config.get('timeout_ticks', TIMEOUT_TICKS)
        timed_out = []
        
        for vid, vehicle in self.vehicles.items():
            if vehicle.wait_ticks >= timeout_limit:
                timed_out.append(vid)
        
        for vid in timed_out:
            vehicle = self.vehicles[vid]
            self.grid.remove_vehicle(vehicle.current_edge, vehicle.cell_pos)
            del self.vehicles[vid]
            self.vehicles_removed_this_tick += 1
    
    def _apply_actions(self, actions: Dict[str, Any]):
        """Apply external actions to simulation.""" 
        if 'spawn_vehicles' in actions:
            count = actions['spawn_vehicles']
            self._spawn_vehicles(count)
        
        if 'traffic_light_overrides' in actions:
            # Handle traffic light manual overrides
            pass  # Could be implemented for advanced control
    
    def _get_current_state(self) -> SimulationState:
        """Get current simulation state."""
        vehicle_states = [self._vehicle_to_state(v) for v in self.vehicles.values()]
        light_states = [self._traffic_light_to_state(l) for l in self.traffic_lights.values()]
        
        active_vehicles = sum(1 for v in self.vehicles.values() if v.velocity > 0)
        
        return SimulationState(
            tick=self.tick,
            vehicles=vehicle_states,
            traffic_lights=light_states,
            total_vehicles=len(self.vehicles),
            active_vehicles=active_vehicles
        )
    
    def _vehicle_to_state(self, vehicle: Vehicle) -> VehicleState:
        """Convert Vehicle to VehicleState for API."""
        # Calculate geographic position
        x, y = self._calculate_geo_position(vehicle)
        
        # Calculate speed in km/h
        speed_kmh = vehicle.velocity * CELL_SIZE_M * 3.6 / TICK_SECONDS
        
        return VehicleState(
            vid=vehicle.vid,
            vtype=vehicle.vtype,
            x=x,
            y=y,
            edge=vehicle.current_edge,
            velocity=vehicle.velocity,
            speed_kmh=round(speed_kmh, 1),
            wait_ticks=vehicle.wait_ticks
        )
    
    def _traffic_light_to_state(self, light: TrafficLight) -> LightState:
        """Convert TrafficLight to LightState for API."""
        node_data = self.topology.nodes[light.node_id]
        phase = light.get_phase(self.tick)
        cycle_pos = light.get_cycle_position(self.tick)
        
        # Calculate time to next phase change
        phase_tick = (self.tick + light.offset_ticks) % light.cycle_ticks
        if phase == "NS_GREEN":
            time_to_change = int(light.cycle_ticks * light.green_ratio) - phase_tick
        else:
            time_to_change = light.cycle_ticks - phase_tick
        
        return LightState(
            node_id=light.node_id,
            phase=phase,
            x=node_data.x,
            y=node_data.y,
            cycle_position=cycle_pos,
            time_to_change=max(0, time_to_change)
        )
    
    def _calculate_geo_position(self, vehicle: Vehicle) -> Tuple[float, float]:
        """Calculate geographic position of vehicle."""
        edge_data = self.topology.edges[vehicle.current_edge]
        geometry_points = edge_data.geometry_points
        
        if len(geometry_points) < 2:
            # Fallback to end node position
            end_node = vehicle.current_edge[1]
            node_data = self.topology.nodes[end_node]
            return node_data.x, node_data.y
        
        # Interpolate along geometry
        edge_length = self.grid.get_edge_length(vehicle.current_edge)
        t = vehicle.cell_pos / max(1, edge_length - 1)
        t = max(0.0, min(1.0, t))
        
        # Linear interpolation between first and last points (simplified)
        start_x, start_y = geometry_points[0]
        end_x, end_y = geometry_points[-1]
        
        x = start_x + t * (end_x - start_x)
        y = start_y + t * (end_y - start_y)
        
        return x, y
    
    def _calculate_metrics(self) -> Metrics:
        """Calculate aggregated simulation metrics."""
        if not self.vehicles:
            return Metrics(
                tick=self.tick,
                total_vehicles=0,
                avg_speed_kmh=0.0,
                density=0.0,
                throughput_veh_per_min=0.0,
                congestion_ratio=0.0,
                boundary_inflow=0.0,
                boundary_outflow=0.0
            )
        
        # Speed metrics
        speeds = [v.velocity * CELL_SIZE_M * 3.6 / TICK_SECONDS for v in self.vehicles.values()]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
        
        # Density
        density = self.grid.get_density()
        
        # Congestion
        stopped_vehicles = sum(1 for v in self.vehicles.values() if v.velocity == 0)
        congestion_ratio = stopped_vehicles / len(self.vehicles)
        
        # Throughput (vehicles per minute)
        throughput = self.vehicles_removed_this_tick * 60.0 / TICK_SECONDS
        inflow = self.vehicles_spawned_this_tick * 60.0 / TICK_SECONDS
        
        return Metrics(
            tick=self.tick,
            total_vehicles=len(self.vehicles),
            avg_speed_kmh=round(avg_speed, 1),
            density=round(density, 3),
            throughput_veh_per_min=round(throughput, 1),
            congestion_ratio=round(congestion_ratio, 3),
            boundary_inflow=round(inflow, 1),
            boundary_outflow=round(throughput, 1)
        )
    
    def _check_termination(self) -> bool:
        """Check if simulation should terminate."""
        max_ticks = self.config.get('max_ticks', 10000)
        return self.tick >= max_ticks
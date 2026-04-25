"""
Pure NaSch (Nagel-Schreckenberg) cellular automata rules.

Implements the four classic NaSch rules as pure functions for reliable,
testable traffic simulation based on the prototype implementation.
"""

import numpy as np
from typing import Dict, Tuple
from ..models import Vehicle, EdgeId
from ...config.constants import CELL_SIZE_M, V_MAX_CELLS


def speed_to_vmax(speed_kph: float, vehicle_factor: float = 1.0) -> int:
    """
    Convert street speed limit to maximum cellular velocity.
    
    Based on prototype speed_to_vmax function with realistic urban parameters.
    
    Args:
        speed_kph: Speed limit in kilometers per hour
        vehicle_factor: Vehicle-specific speed multiplier
        
    Returns:
        Maximum velocity in cells per tick, clamped to [1, V_MAX_CELLS]
        
    Note:
        - Minimum 20 km/h (residential), maximum 60 km/h (highways)
        - Conversion: km/h → m/s → cells/s → cells/tick
        - Vehicle factor allows differentiation (cars=1.0, buses=0.55, motos=1.25)
    """
    # Clamp to realistic urban speed range
    speed_kph = max(20.0, min(60.0, speed_kph))
    
    # Convert to cells per second, then to cells per tick
    cells_per_sec = speed_kph / 3.6 / CELL_SIZE_M
    cells_per_tick = cells_per_sec * 1.0  # TICK_SECONDS = 1.0
    
    # Apply vehicle factor and clamp to valid range
    effective_cells = cells_per_tick * vehicle_factor
    return max(1, min(V_MAX_CELLS, round(effective_cells)))


def nasch_rule_1_acceleration(current_velocity: int, vmax: int) -> int:
    """
    NaSch Rule 1: Acceleration.
    
    If v < v_max, then v → v + 1
    
    Args:
        current_velocity: Current velocity in cells/tick
        vmax: Maximum allowed velocity for this vehicle/edge
        
    Returns:
        Velocity after acceleration rule (clamped to vmax)
    """
    return min(current_velocity + 1, vmax)


def nasch_rule_2_braking(velocity_after_rule1: int, gap_ahead: int) -> int:
    """
    NaSch Rule 2: Collision avoidance (braking).
    
    If gap < v, then v → gap
    
    Args:
        velocity_after_rule1: Velocity after rule 1 (acceleration)
        gap_ahead: Number of free cells ahead of vehicle
        
    Returns:
        Velocity after braking rule (reduced if necessary to avoid collision)
    """
    return min(velocity_after_rule1, gap_ahead)


def nasch_rule_3_randomization(velocity_after_rule2: int, noise_prob: float, rng: np.random.Generator) -> int:
    """
    NaSch Rule 3: Random deceleration (noise).
    
    If v > 0 and random() < p_noise, then v → v - 1
    
    Args:
        velocity_after_rule2: Velocity after rule 2 (braking)
        noise_prob: Probability of random deceleration [0,1]
        rng: Random number generator for reproducibility
        
    Returns:
        Velocity after randomization (may be reduced by 1 with probability noise_prob)
    """
    if velocity_after_rule2 > 0 and rng.random() < noise_prob:
        return max(0, velocity_after_rule2 - 1)
    return velocity_after_rule2


def nasch_rule_4_movement(current_position: int, final_velocity: int) -> int:
    """
    NaSch Rule 4: Movement.
    
    x → x + v
    
    Args:
        current_position: Current position in cells
        final_velocity: Final velocity after rules 1-3
        
    Returns:
        New position after movement
    """
    return current_position + final_velocity


def calculate_gap_same_edge(edge_cells: np.ndarray, vehicle_position: int) -> int:
    """
    Calculate gap to next vehicle on same edge.
    
    Args:
        edge_cells: Array of vehicle IDs (0=empty, >0=vehicle ID)
        vehicle_position: Current position of vehicle in cells
        
    Returns:
        Number of free cells ahead before next vehicle or end of edge
    """
    edge_length = len(edge_cells)
    
    # Search ahead for next obstacle
    for distance in range(1, edge_length - vehicle_position):
        check_pos = vehicle_position + distance
        if edge_cells[check_pos] != 0:  # Found vehicle
            return distance - 1
    
    # No vehicle found, gap extends to end of edge
    return (edge_length - 1) - vehicle_position


def calculate_gap_cross_edge(
    current_edge_cells: np.ndarray,
    current_position: int,
    next_edge_cells: np.ndarray
) -> int:
    """
    Calculate gap that spans across edge boundary.
    
    Args:
        current_edge_cells: Cells array for current edge
        current_position: Position in current edge
        next_edge_cells: Cells array for next edge
        
    Returns:
        Total gap spanning both edges
    """
    # Gap to end of current edge
    current_edge_length = len(current_edge_cells)
    gap_to_end = (current_edge_length - 1) - current_position
    
    # Gap at beginning of next edge
    gap_in_next = 0
    for i, cell in enumerate(next_edge_cells):
        if cell != 0:  # Found vehicle
            break
        gap_in_next += 1
    
    return gap_to_end + gap_in_next


def apply_nasch_rules(
    vehicle: Vehicle,
    edge_cells: Dict[EdgeId, np.ndarray],
    edge_vmax: Dict[EdgeId, int],
    traffic_light_green: bool,
    rng: np.random.Generator
) -> int:
    """
    Apply all four NaSch rules to calculate new velocity.
    
    Args:
        vehicle: Vehicle to update
        edge_cells: Dictionary of edge cell arrays (for gap calculation)
        edge_vmax: Dictionary of maximum velocities by edge
        traffic_light_green: True if traffic light allows passage
        rng: Random number generator
        
    Returns:
        New velocity after applying all NaSch rules
    """
    # Get vehicle parameters
    current_edge = vehicle.current_edge
    vmax_base = edge_vmax[current_edge]
    vehicle_config = vehicle.get_config()
    
    # Calculate effective vmax for this vehicle
    effective_vmax = max(1, round(vmax_base * vehicle.vmax_factor * vehicle_config.speed_factor))
    
    # Rule 1: Acceleration
    velocity = nasch_rule_1_acceleration(vehicle.velocity, effective_vmax)
    
    # Rule 2: Braking (gap calculation)
    gap = calculate_gap_same_edge(edge_cells[current_edge], vehicle.cell_pos)
    
    # Traffic light constraint: can't proceed beyond edge if light is red
    if not traffic_light_green and vehicle.next_edge is not None:
        # Limit gap to edge boundary
        current_edge_length = len(edge_cells[current_edge])
        gap_to_boundary = (current_edge_length - 1) - vehicle.cell_pos
        gap = min(gap, gap_to_boundary)
    
    # Gap extension to next edge if light is green and next edge exists
    if traffic_light_green and vehicle.next_edge is not None and gap > 0:
        next_edge = vehicle.next_edge
        if next_edge in edge_cells:
            total_gap = calculate_gap_cross_edge(
                edge_cells[current_edge], 
                vehicle.cell_pos,
                edge_cells[next_edge]
            )
            gap = total_gap
    
    velocity = nasch_rule_2_braking(velocity, gap)
    
    # Rule 3: Randomization 
    velocity = nasch_rule_3_randomization(velocity, vehicle.noise_prob, rng)
    
    return velocity
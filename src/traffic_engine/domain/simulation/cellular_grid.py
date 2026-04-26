"""
Cellular grid management for traffic simulation.

Handles the discrete cellular automata representation of the road network,
including edge discretization, vehicle placement, and atomic movements.
"""

import numpy as np
from typing import Dict, List

from ..models import TopologyData, EdgeId, Vehicle


class CellularGrid:
    """
    Manages the cellular automata grid for traffic simulation.
    
    Handles discretization of the road network into cells and provides
    atomic operations for vehicle placement and movement with conflict resolution.
    """
    
    def __init__(self, topology: TopologyData):
        """
        Initialize cellular grid from topology data.
        
        Args:
            topology: Road network topology with discretization info
        """
        self.topology = topology
        self.edge_cells: Dict[EdgeId, np.ndarray] = {}
        self.edge_lengths: Dict[EdgeId, int] = {}
        self.edge_lanes: Dict[EdgeId, int] = {}
        
        for edge_id, edge_data in topology.edges.items():
            n_cells = max(1, int(edge_data.n_cells))
            n_lanes = max(1, int(getattr(edge_data, 'n_lanes', 1)))
            self.edge_cells[edge_id] = np.zeros((n_lanes, n_cells), dtype=np.int32)
            self.edge_lengths[edge_id] = n_cells
            self.edge_lanes[edge_id] = n_lanes
    
    def get_edge_cells(self, edge_id: EdgeId) -> np.ndarray:
        """Get cell array for specific edge."""
        return self.edge_cells[edge_id]
    
    def get_edge_length(self, edge_id: EdgeId) -> int:
        """Get number of cells in specific edge."""
        return self.edge_lengths[edge_id]

    def get_edge_lane_count(self, edge_id: EdgeId) -> int:
        """Get lane count for specific edge."""
        return self.edge_lanes[edge_id]

    def _validate_lane_index(self, edge_id: EdgeId, lane_index: int) -> None:
        if lane_index < 0 or lane_index >= self.edge_lanes[edge_id]:
            raise ValueError(
                f"Lane index {lane_index} is out of bounds for edge {edge_id} with {self.edge_lanes[edge_id]} lanes."
            )
    
    def is_cell_occupied(self, edge_id: EdgeId, position: int, lane_index: int = 0) -> bool:
        """Check if cell is occupied by a vehicle."""
        self._validate_lane_index(edge_id, lane_index)
        if position < 0 or position >= self.edge_lengths[edge_id]:
            return True
        return bool(self.edge_cells[edge_id][lane_index, position] != 0)
    
    def get_vehicle_at_cell(self, edge_id: EdgeId, position: int, lane_index: int = 0) -> int:
        """Get vehicle ID at specific cell (0 if empty)."""
        self._validate_lane_index(edge_id, lane_index)
        if position < 0 or position >= self.edge_lengths[edge_id]:
            return 0
        return int(self.edge_cells[edge_id][lane_index, position])
    
    def place_vehicle(
        self,
        edge_id: EdgeId,
        position: int,
        vehicle_id: int,
        lane_index: int = 0,
    ) -> bool:
        """
        Place vehicle in specific cell if it's free.
        
        Args:
            edge_id: Target edge
            position: Target position in cells
            vehicle_id: Vehicle identifier
            
        Returns:
            True if placement successful, False if cell occupied or invalid
        """
        self._validate_lane_index(edge_id, lane_index)
        if position < 0 or position >= self.edge_lengths[edge_id]:
            return False
        if self.edge_cells[edge_id][lane_index, position] != 0:
            return False

        self.edge_cells[edge_id][lane_index, position] = int(vehicle_id)
        return True
    
    def remove_vehicle(self, edge_id: EdgeId, position: int, lane_index: int = 0) -> bool:
        """
        Remove vehicle from specific cell.
        
        Args:
            edge_id: Edge containing the vehicle
            position: Position to clear
            
        Returns:
            True if removal successful, False if cell was already empty
        """
        self._validate_lane_index(edge_id, lane_index)
        if position < 0 or position >= self.edge_lengths[edge_id]:
            return False
        
        if self.edge_cells[edge_id][lane_index, position] == 0:
            return False
        
        self.edge_cells[edge_id][lane_index, position] = 0
        return True
    
    def move_vehicle_atomic(
        self, 
        old_edge: EdgeId, 
        old_position: int,
        new_edge: EdgeId, 
        new_position: int,
        vehicle_id: int,
        old_lane_index: int = 0,
        new_lane_index: int = 0,
    ) -> bool:
        """
        Move vehicle atomically from old to new position.
        
        Args:
            old_edge: Current edge
            old_position: Current position
            new_edge: Target edge
            new_position: Target position
            vehicle_id: Vehicle identifier for verification
            
        Returns:
            True if move successful, False if target occupied or verification failed
        """
        self._validate_lane_index(old_edge, old_lane_index)
        self._validate_lane_index(new_edge, new_lane_index)

        if (
            old_position >= 0
            and old_position < self.edge_lengths[old_edge]
            and self.edge_cells[old_edge][old_lane_index, old_position] != vehicle_id
        ):
            return False

        if new_position < 0 or new_position >= self.edge_lengths[new_edge]:
            return False
        if self.edge_cells[new_edge][new_lane_index, new_position] != 0:
            return False

        if old_position >= 0 and old_position < self.edge_lengths[old_edge]:
            self.edge_cells[old_edge][old_lane_index, old_position] = 0
        self.edge_cells[new_edge][new_lane_index, new_position] = int(vehicle_id)
        return True
    
    def find_free_cells(self, edge_id: EdgeId, count: int = 1, lane_index: int = 0) -> List[int]:
        """
        Find free cells on edge for vehicle spawning.
        
        Args:
            edge_id: Edge to search
            count: Maximum number of free cells to return
            
        Returns:
            List of free cell positions (may be shorter than count)
        """
        self._validate_lane_index(edge_id, lane_index)
        edge_cells = self.edge_cells[edge_id][lane_index]
        free_positions = np.where(edge_cells == 0)[0]
        return free_positions[:count].tolist()
    
    def get_total_cells(self) -> int:
        """Get total number of cells in the network."""
        return sum(cells.size for cells in self.edge_cells.values())
    
    def get_occupied_cells(self) -> int:
        """Get total number of occupied cells."""
        occupied = 0
        for edge_cells in self.edge_cells.values():
            occupied += int(np.sum(edge_cells > 0))
        return occupied
    
    def get_density(self) -> float:
        """Get overall network density (fraction of cells occupied)."""
        total = self.get_total_cells()
        occupied = self.get_occupied_cells()
        return occupied / max(1, total)
    
    def get_edge_density(self, edge_id: EdgeId) -> float:
        """Get density for specific edge."""
        edge_cells = self.edge_cells[edge_id]
        occupied = int(np.sum(edge_cells > 0))
        return occupied / max(1, edge_cells.size)
    
    def get_edge_flow(self, edge_id: EdgeId) -> int:
        """Get current vehicle count on specific edge."""
        return int(np.sum(self.edge_cells[edge_id] > 0))
    
    def verify_integrity(self, vehicles: Dict[int, Vehicle]) -> List[str]:
        """
        Verify grid integrity and consistency with vehicle objects.
        
        Args:
            vehicles: Dictionary of vehicle objects to cross-check
            
        Returns:
            List of integrity errors (empty if no errors)
        """
        errors = []
        
        all_vids = []
        for edge_cells in self.edge_cells.values():
            vids = edge_cells[edge_cells > 0]
            all_vids.extend(vids.tolist())
        
        if len(all_vids) != len(set(all_vids)):
            errors.append("Duplicate vehicle IDs found in grid")
        
        for vid, vehicle in vehicles.items():
            expected_pos = vehicle.cell_pos
            expected_lane = int(getattr(vehicle, 'lane_index', 0))
            expected_edge = vehicle.current_edge
            
            if expected_edge not in self.edge_cells:
                errors.append(f"Vehicle {vid} on unknown edge {expected_edge}")
                continue

            if expected_lane < 0 or expected_lane >= self.edge_lanes[expected_edge]:
                errors.append(
                    f"Vehicle {vid} in invalid lane {expected_lane} on edge {expected_edge}"
                )
                continue
            
            if (expected_pos < 0 or expected_pos >= self.edge_lengths[expected_edge]):
                errors.append(f"Vehicle {vid} at invalid position {expected_pos} on edge {expected_edge}")
                continue
                
            actual_vid = int(self.edge_cells[expected_edge][expected_lane, expected_pos])
            if actual_vid != vid:
                errors.append(
                    f"Vehicle {vid} position mismatch: grid has {actual_vid} at "
                    f"{expected_edge}[lane={expected_lane}, cell={expected_pos}]"
                )
        
        return errors
    
    def clear(self):
        """Clear all vehicles from the grid."""
        for edge_id in self.edge_cells:
            self.edge_cells[edge_id].fill(0)
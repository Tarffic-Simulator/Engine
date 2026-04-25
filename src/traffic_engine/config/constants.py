"""
Configuration constants for traffic simulation engine.

These constants define the physical parameters and simulation behavior,
extracted from the prototype implementation to maintain consistency.
"""

# Physical Parameters
CELL_SIZE_M = 5.0       # Cell size in meters (finer discretization than prototype 7.5m)
TICK_SECONDS = 1.0      # Simulation time step in seconds
V_MAX_CELLS = 5         # Maximum velocity in cells per tick

# NaSch Model Parameters  
NOISE_PROB = 0.28       # Base probability of random braking
TIMEOUT_TICKS = 50      # Consecutive ticks stationary before vehicle "parks" and disappears

# Boundary Flow Parameters
ENTRY_PROB = 0.55       # Probability that vehicle origin is boundary node
EXIT_PROB = 0.70        # Probability that vehicle destination is boundary node
BOUNDARY_MARGIN = 0.14  # Fraction of bbox considered "boundary" for inflow/outflow

# Vehicle Type Configuration
VEHICLE_TYPE_WEIGHTS = [0.75, 0.15, 0.10]  # Probabilities for [car, bus, moto]

# Traffic Light Configuration  
DEFAULT_CYCLE_TICKS = 30    # Default traffic light cycle duration
DEFAULT_GREEN_RATIO = 0.5   # Default fraction of cycle that is green (for NS phase)

# API Configuration
MAX_SIMULATION_SESSIONS = 100   # Maximum concurrent simulation sessions
SESSION_TTL_MINUTES = 60       # Session timeout in minutes
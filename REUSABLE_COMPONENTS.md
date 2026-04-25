# Reusable Components

This file tracks components with reuse potential across the Traffic Engine project.

## Core Domain Models

### VehicleState (src/traffic_engine/domain/models/vehicles.py)

**Problem it solves**: Standardized representation of vehicle state for API responses and visualization.

**How to reuse/extend**: Can be extended with additional fields for more detailed vehicle tracking. The dataclass structure makes it easy to serialize/deserialize for different output formats.

### Metrics (src/traffic_engine/domain/models/simulation_state.py)  

**Problem it solves**: Consistent aggregated metrics collection across different simulation implementations.

**How to reuse/extend**: Fields can be added for new KPIs. The structure supports both real-time monitoring and historical analysis.

### SimulationState (src/traffic_engine/domain/models/simulation_state.py)

**Problem it solves**: Complete snapshot of simulation state at any point in time.

**How to reuse/extend**: Can be extended with additional state components. Useful for state persistence, replay functionality, and debugging.

## Infrastructure Components

### OSMnxTopologyProvider (src/traffic_engine/infrastructure/topology/osmnx_provider.py)

**Problem it solves**: Loads real road network data from OpenStreetMap via OSMnx.

**How to reuse/extend**: Can be extended to support different geographic queries, caching strategies, or custom road network filters.

### SimulationManager (src/traffic_engine/api/simulation_manager.py)

**Problem it solves**: Manages multiple concurrent simulation instances with automatic cleanup and resource management.

**How to reuse/extend**: The pattern can be applied to other stateful services needing instance management. Cleanup policies and resource limits are configurable.

## Application Layer Components

### Use Case Pattern (src/traffic_engine/application/use_cases/)

**Problem it solves**: Encapsulates business logic in discrete, testable operations following clean architecture principles.

**How to reuse/extend**: The pattern can be extended for new simulation operations. Each use case is self-contained with clear input/output contracts.

### Contract DTOs (src/traffic_engine/application/contracts/simulation_dto.py)

**Problem it solves**: Clean separation between API layer and application layer with type-safe data transfer objects.

**How to reuse/extend**: New request/response types can follow the same dataclass pattern. Validation can be added through `__post_init__` methods.

## API Components

### FastAPI Application Structure (src/traffic_engine/api/app.py)

**Problem it solves**: RESTful API with automatic OpenAPI documentation and request validation.

**How to reuse/extend**: The endpoint patterns can be extended for new simulation operations. CORS and middleware configuration is centralized.

## 2026-04-24 Iteration 1

### API DTO Translation (src/traffic_engine/api/app.py)

**Problem it solves**: Converts public FastAPI Pydantic models into internal application DTOs without coupling the API layer to dataclass contracts.

**How to reuse/extend**: Additional endpoints can follow the same translation pattern to keep API schemas stable while application internals evolve.

### NaSch Simulation Core (src/traffic_engine/domain/simulation/nasch_model.py)

**Problem it solves**: Provides a reusable NaSch simulation engine with deterministic reset and step behavior over TopologyData inputs.

**How to reuse/extend**: Small topologies can use the same model directly for smoke tests, CLI experiments, or future service adapters.

### Real Engine Smoke Test (tests/test_real_engine_smoke.py)

**Problem it solves**: Validates the generated package with a minimal real-module integration check instead of mocks.

**How to reuse/extend**: Future migration slices can add narrow runtime assertions here before widening to broader suite coverage.

## 2026-04-24 Iteration 2

### Snapshot DTO Validation Path (src/traffic_engine/api/app.py)

**Problem it solves**: Converts invalid `vehicle_types_filter` query values into a stable FastAPI 422 response instead of leaking enum construction failures.

**How to reuse/extend**: Other enum-backed query translators can follow the same pattern to keep transport-layer validation errors consistent.

### Prototype Speed Attribute Fallback (src/traffic_engine/infrastructure/topology/topology_converter.py)

**Problem it solves**: Normalizes prototype and fixture edge speed attributes across `maxspeed` and `speed_kph` during topology conversion.

**How to reuse/extend**: Additional legacy attribute aliases can be added in one place without changing the rest of the discretization pipeline.

## 2026-04-24 Iteration 3

### Pytest Baseline Configuration (pytest.ini)

**Problem it solves**: Keeps pytest startup compatible with INI syntax so narrow smoke validations can run before broader suite work.

**How to reuse/extend**: Future test-runner options can be added here, but Python-list style values should stay in Python files or TOML rather than `pytest.ini`.

## 2026-04-24 Iteration 5

### ReplayAndStreamTicksUseCase (src/traffic_engine/application/use_cases/replay_and_stream_ticks.py)

**Problem it solves**: Replays persisted tick history and serializes deterministic SSE payloads with `Last-Event-ID` recovery semantics.

**How to reuse/extend**: Future transports can reuse the replay ordering and reconnection logic while swapping only the final event serialization layer.

### Mongo Realtime Repositories (src/traffic_engine/infrastructure/persistence/mongo_realtime_repositories.py)

**Problem it solves**: Stores session metadata, execution runs, and high-frequency tick history in separate MongoDB collections with replay-friendly indexes.

**How to reuse/extend**: Additional operational queries or retention policies can be added in one persistence module without leaking Mongo details into the application layer.

### InProcessRunExecutor (src/traffic_engine/infrastructure/runtime/in_process_run_executor.py)

**Problem it solves**: Schedules realtime runs asynchronously behind a replaceable executor contract for local and development execution.

**How to reuse/extend**: A worker-backed executor can implement the same `submit` and `shutdown` surface while preserving API and application use cases.

## 2026-04-24 Iteration 6

### SimulationRuntimeGateway (src/traffic_engine/application/contracts/realtime_runtime.py)

**Problem it solves**: Defines a narrow application-owned contract for synchronous simulation creation and stepping so realtime runtime adapters can reuse orchestration logic without importing API modules.

**How to reuse/extend**: Any future simulation facade or legacy manager can implement the same two-method gateway and be injected into realtime adapters without changing the application or SSE orchestration code.

### close_mongo_client lifecycle guard (src/traffic_engine/infrastructure/persistence/mongodb.py)

**Problem it solves**: Makes MongoDB client shutdown idempotent so API lifecycle hooks can safely release cached clients without forcing initialization or crashing when Mongo was never opened.

**How to reuse/extend**: Other startup and shutdown paths can call the same helper directly whenever they need safe cached-client teardown across tests, CLIs, or alternate web entry points.

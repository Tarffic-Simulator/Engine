# Reusable Components

This file tracks components with reuse potential across the active Traffic Engine scope.

Last updated: 2026-04-26

## Domain and Application Reuse Map

| Component | Location | Problem it solves | How to reuse or extend |
| --- | --- | --- | --- |
| NaSch simulation core | `src/traffic_engine/domain/simulation/nasch_model.py` | Provides deterministic reset/step behavior over topology-backed cellular state. | Reuse directly for smoke tests, experiments, or alternate service adapters that need the same domain engine. |
| Lane-aware snapshot serialization | `src/traffic_engine/application/use_cases/get_snapshot.py` | Converts domain state into additive vehicle, light, and edge payloads suitable for API and realtime replay. | Extend this boundary when new visualization or analytics fields are needed without exposing domain internals. |
| Public lifecycle normalization helpers | `src/traffic_engine/application/contracts/realtime_entities.py` | Maps internal lifecycle terms to the public contract vocabulary used by HTTP and WebSocket consumers. | Reuse from any new API response model, filter, or streaming adapter that surfaces realtime status. |
| ExtendRealtimeSessionUseCase | `src/traffic_engine/application/use_cases/extend_realtime_session.py` | Creates a new run under a finished session while preventing concurrent active-run conflicts. | Reuse from future admin tooling or alternate runtime adapters that need restart or extension semantics. |
| StreamRealtimeEventsUseCase | `src/traffic_engine/application/use_cases/stream_realtime_events.py` | Replays persisted ticks and follows live broker events through one transport-neutral envelope shape. | Reuse from WebSocket handlers, compatibility transports, or CLI watchers without importing FastAPI primitives. |

## Infrastructure Reuse Map

| Component | Location | Problem it solves | How to reuse or extend |
| --- | --- | --- | --- |
| Mongo realtime repositories | `src/traffic_engine/infrastructure/persistence/mongo_realtime_repositories.py` | Stores sessions, runs, and ticks in separate collections with replay-friendly queries. | Extend here for retention jobs, reporting queries, or new repository methods without leaking MongoDB logic upward. |
| InProcessRunExecutor | `src/traffic_engine/infrastructure/runtime/in_process_run_executor.py` | Schedules realtime runs asynchronously behind the `RunExecutor` contract for local/dev execution. | Replace with a worker-backed adapter that preserves the same `submit` and `shutdown` surface. |
| ManagerBackedSimulationModel | `src/traffic_engine/infrastructure/runtime/manager_backed_simulation_model.py` | Bridges the existing synchronous manager path into the realtime runtime without exposing API modules to application code. | Reuse the same pattern when wrapping another stateful synchronous engine behind a smaller application-owned gateway. |
| OSMnx helper resolution bridge | `src/traffic_engine/infrastructure/topology/osmnx_provider.py` | Shields topology loading from OSMnx helper namespace drift across versions. | Apply the same boundary pattern to other third-party integrations whose helper locations change over time. |
| `close_mongo_client` lifecycle guard | `src/traffic_engine/infrastructure/persistence/mongodb.py` | Makes MongoDB client shutdown idempotent across API, tests, and local tooling. | Reuse whenever startup/shutdown paths need safe cached-client teardown. |

## API and Test Reuse Map

| Component | Location | Problem it solves | How to reuse or extend |
| --- | --- | --- | --- |
| API DTO translation helpers | `src/traffic_engine/api/app.py` | Converts Pydantic request models into application DTOs without coupling transport schemas to internal dataclasses. | Follow the same translation pattern for any new endpoint that should keep transport and application contracts separate. |
| SimulationManager | `src/traffic_engine/api/simulation_manager.py` | Owns UUID-scoped synchronous simulation lifecycle and isolates concurrent simulation state. | Reuse the same management pattern for other stateful engine surfaces that need bounded instance tracking. |
| Real engine smoke test | `tests/test_real_engine_smoke.py` | Validates the installed package with a narrow real-module execution path instead of mocks. | Add future runtime assertions here before widening to broader integration slices. |
| Physical configuration fixtures | `tests/conftest.py` and `tests/test_physical_config.py` | Provide stable config and topology test data for low-cost validation of conversion helpers. | Reuse when adding new provider or physical-parameter tests that need small deterministic graphs. |

## Notes

1. This document tracks only components that still exist in the active repository scope.
2. Historical client-UI components were removed from the active reuse map during the documentation synchronization step.

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

## 2026-04-25 Iteration 9

### Snapshot Simulation Test Double (tests/test_snapshot_lane_payloads.py)

**Problem it solves**: Provides a deterministic snapshot fixture whose vehicle and edge state can be mutated in-place so serialization contracts can verify lane-aware shape changes.

**How to reuse/extend**: Additional snapshot contract tests can extend the same fake with new edge or vehicle attributes instead of rebuilding bespoke simulation stubs for each payload variation.

**How to reuse/extend**: A worker-backed executor can implement the same `submit` and `shutdown` surface while preserving API and application use cases.

## 2026-04-24 Iteration 6

### SimulationRuntimeGateway (src/traffic_engine/application/contracts/realtime_runtime.py)

**Problem it solves**: Defines a narrow application-owned contract for synchronous simulation creation and stepping so realtime runtime adapters can reuse orchestration logic without importing API modules.

**How to reuse/extend**: Any future simulation facade or legacy manager can implement the same two-method gateway and be injected into realtime adapters without changing the application or SSE orchestration code.

### close_mongo_client lifecycle guard (src/traffic_engine/infrastructure/persistence/mongodb.py)

**Problem it solves**: Makes MongoDB client shutdown idempotent so API lifecycle hooks can safely release cached clients without forcing initialization or crashing when Mongo was never opened.

**How to reuse/extend**: Other startup and shutdown paths can call the same helper directly whenever they need safe cached-client teardown across tests, CLIs, or alternate web entry points.

## 2026-04-25 Iteration 7

### GetSnapshotUseCase lane-aware payload serialization (src/traffic_engine/application/use_cases/get_snapshot.py)

**Problem it solves**: Preserves additive multicarril and rendering metadata such as `lane_index`, `lateral_offset_m`, `render_label`, `render_color`, `n_lanes`, and `occupancy_cells_lane_major` in snapshot payloads consumed by the dashboard and realtime persistence.

**How to reuse/extend**: Future visualization-only fields can be added in the same serialization boundary without changing the domain state model or breaking backward-compatible payload consumers.

### ManagerBackedSimulationModel snapshot normalization (src/traffic_engine/infrastructure/runtime/manager_backed_simulation_model.py)

**Problem it solves**: Normalizes legacy manager snapshot responses so realtime execution returns the full post-step state needed by persistence and SSE contracts, not only tick counters.

**How to reuse/extend**: Other runtime adapters can reuse the same pattern when they need to bridge between object-based and dict-based manager facades while keeping the application-facing state contract stable.

## 2026-04-25 Iteration 8

### NaSch gap helpers (src/traffic_engine/domain/simulation/nasch_rules.py)

**Problem it solves**: Keeps same-edge and cross-edge gap calculations small and deterministic for the core NaSch rule application path.

**How to reuse/extend**: Future movement or lane-selection rules can keep calling the same helpers as long as they continue to operate on resolved lane occupancy arrays instead of transport-layer payloads.

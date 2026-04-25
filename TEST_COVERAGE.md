# Test Coverage Report — CDMX Traffic Engine TDD Suite

## Overview

This document tracks the comprehensive test suite created for the CDMX traffic simulation engine following Test-Driven Development (TDD) principles. All tests define expected contracts and behavior **before implementation**, ensuring clear requirements and design validation.

---

## Test Structure Summary

| Test Module | Purpose | Test Count | Coverage Focus |
|-------------|---------|------------|----------------|
| `test_physical_config.py` | Physical parameter validation | 15 tests | Speed conversion, vehicle types, boundary detection |
| `test_domain_models.py` | Core domain entities | 18 tests | Topology, vehicles, simulation state, traffic lights |
| `test_nasch_simulation.py` | NaSch algorithm & cellular automata | 20 tests | 4 NaSch rules, gap calculation, synchronous execution |
| `test_providers.py` | External data provider contracts | 16 tests | Topology & traffic light provider interfaces |
| `test_use_cases.py` | Application orchestration logic | 20 tests | Create, step, metrics, snapshot use cases |
| `test_api_layer.py` | FastAPI endpoints & session management | 16 tests | REST API, simulation manager, Pydantic schemas |
| **Total** | **Comprehensive coverage** | **105 tests** | **End-to-end contracts** |

---

## Coverage Analysis by Component

### 1. Physical Configuration (`test_physical_config.py`)

#### Functions/Classes Analyzed:
- `speed_to_vmax()` conversion logic
- Vehicle type parameter configurations
- Boundary node detection algorithms
- Configuration parameter validation

#### Scenarios Covered:
- **Happy Path**: Standard CDMX speed limits (30, 50, 70 km/h) convert to reasonable cell velocities
- **Edge Cases**: Extreme speeds (5, 200 km/h) handled with min/max clamping
- **Alternative Cases**: Vehicle type factors (car=1.0, bus=0.55, moto=1.25) apply correctly
- **Expected Errors**: Invalid configuration parameters rejected

#### Scenarios Excluded:
- OSM-specific coordinate transformations (delegated to infrastructure layer)
- Real-world GPS precision issues (out of scope for cellular model)

#### Identified Risks:
- Speed conversion accuracy affects simulation realism
- Boundary detection algorithm may miss complex highway interchanges

---

### 2. Domain Models (`test_domain_models.py`)

#### Functions/Classes Analyzed:
- `TopologyData` structure and validation
- `Vehicle` entity with position tracking
- `SimulationState` metrics and snapshots
- `TrafficLight` phase logic and edge classification

#### Scenarios Covered:
- **Happy Path**: Well-formed topology with valid nodes/edges/bbox
- **Edge Cases**: Empty vehicle lists, single-node networks, extreme coordinates
- **Alternative Cases**: Different vehicle types, various traffic light configurations
- **Expected Errors**: Malformed topology data, invalid vehicle routes

#### Scenarios Excluded:
- NetworkX-specific graph algorithms (abstracted by providers)
- Geographic projection mathematics (handled by infrastructure)

#### Identified Risks:
- Edge discretization precision affects vehicle movement accuracy
- Traffic light bearing calculations may fail near poles/dateline

---

### 3. NaSch Simulation (`test_nasch_simulation.py`)

#### Functions/Classes Analyzed:
- NaSch 4-rule algorithm (acceleration, braking, noise, movement)
- Gap calculation logic across edge boundaries
- Cellular grid management and collision prevention
- Gymnasium-like simulation model interface

#### Scenarios Covered:
- **Happy Path**: Normal NaSch execution with typical gaps and velocities
- **Edge Cases**: Zero velocity, maximum velocity, empty edges, red lights
- **Alternative Cases**: Cross-edge movement, vehicle spawning, different noise probabilities
- **Expected Errors**: Invalid simulation parameters, edge overflow handling

#### Scenarios Excluded:
- Real-world driver psychology (beyond stochastic noise)
- Vehicle-specific acceleration curves (simplified to discrete cells)
- Multi-lane interactions (current model is single-lane per edge)

#### Identified Risks:
- Synchronous execution complexity may introduce race conditions
- Gap calculation across many edges could impact performance

---

### 4. Provider Interfaces (`test_providers.py`)

#### Functions/Classes Analyzed:
- `TopologyProvider` interface (load_area, load_bbox)
- `TrafficLightProvider` interface (get_lights, update_config)
- OSMnx NetworkX conversion logic
- Centrality-based traffic light placement

#### Scenarios Covered:
- **Happy Path**: Successful data loading from providers
- **Edge Cases**: Empty areas, invalid coordinates, provider failures
- **Alternative Cases**: Different data sources, cached vs. fresh data
- **Expected Errors**: Network failures, invalid area names, malformed data

#### Scenarios Excluded:
- OSMnx API rate limiting (external service concern)
- Real traffic light timing data (not available for CDMX)

#### Identified Risks:
- Provider failures could halt simulation creation
- Centrality calculations may be expensive for large networks

---

### 5. Use Cases (`test_use_cases.py`)

#### Functions/Classes Analyzed:
- `CreateSimulationUseCase` orchestration
- `StepSimulationUseCase` execution
- `GetMetricsUseCase` aggregation
- `GetSnapshotUseCase` state extraction

#### Scenarios Covered:
- **Happy Path**: Successful use case execution with valid inputs
- **Edge Cases**: Empty simulations, large step counts, concurrent access
- **Alternative Cases**: Different configurations, various action types
- **Expected Errors**: Invalid parameters, provider failures, missing simulations

#### Scenarios Excluded:
- Complex multi-user authorization (authentication is API gateway concern)
- Long-running simulation persistence (future database integration)

#### Identified Risks:
- Use case orchestration complexity may introduce coupling
- Metrics calculation performance for large simulations

---

### 6. API Layer (`test_api_layer.py`)

#### Functions/Classes Analyzed:
- `SimulationManager` session lifecycle
- FastAPI endpoint contracts (POST, GET, PUT, DELETE)
- Pydantic request/response schemas
- Session cleanup and memory management

#### Scenarios Covered:
- **Happy Path**: Valid HTTP requests and responses
- **Edge Cases**: Concurrent requests, session expiration, memory limits
- **Alternative Cases**: Different request formats, optional parameters
- **Expected Errors**: Invalid JSON, missing fields, 404/422 status codes

#### Scenarios Excluded:
- HTTP connection-level issues (handled by uvicorn/FastAPI)
- Authentication/authorization (deferred to API gateway)
- Rate limiting and DoS protection (infrastructure concern)

#### Identified Risks:
- Session cleanup may be too aggressive or too lenient
- Concurrent access to same simulation needs careful synchronization

---

## Test Execution Commands

### Run Full Suite
```bash
# Run all tests with verbose output
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=src/traffic_engine --cov-report=html

# Run specific test categories
pytest -m "domain" tests/          # Domain model tests only
pytest -m "api" tests/             # API layer tests only
pytest -m "simulation" tests/      # NaSch simulation tests only
```

### Run by Component
```bash
pytest tests/test_physical_config.py    # Physical configuration
pytest tests/test_domain_models.py      # Domain entities  
pytest tests/test_nasch_simulation.py   # NaSch algorithm
pytest tests/test_providers.py          # Provider interfaces
pytest tests/test_use_cases.py          # Application logic
pytest tests/test_api_layer.py          # REST API & session management
```

### Run Specific Test Scenarios
```bash
# Test specific functionality
pytest -k "speed_conversion" tests/          # Speed-to-vmax conversion
pytest -k "traffic_light" tests/             # Traffic light behavior
pytest -k "nasch_rules" tests/               # NaSch 4-rule algorithm
pytest -k "api_validation" tests/            # API request/response validation
```

---

## Test Dependencies & Fixtures

### Shared Fixtures (in `conftest.py`)
- `simple_network`: 4-node diamond NetworkX graph for basic testing
- `linear_network`: 3-node chain for edge transition testing  
- `intersection_network`: 4-way intersection for traffic light testing
- `vehicle_types_config`: Standard CAR/BUS/MOTO configurations
- `simulation_config`: Default simulation parameters
- `mock_topology_data`: Sample TopologyData without NetworkX dependency

### External Dependencies (Test-Only)
- `pytest`: Test framework and fixtures
- `unittest.mock`: Mocking external services and providers
- `networkx`: Small test networks (replaced by TopologyData in production)

### No Heavy Dependencies
- ❌ **No OSMnx in tests**: All topology loading mocked
- ❌ **No real CDMX data**: Small synthetic networks only  
- ❌ **No HTTP clients**: FastAPI endpoints mocked
- ❌ **No database**: All persistence mocked

---

## Implementation Readiness

### Tests Expected to Initially Fail ✅
This is **correct TDD behavior**. Tests define contracts before implementation:

1. **Domain Models**: Tests expect dataclasses/entities that don't exist yet
2. **NaSch Algorithm**: Tests expect `NaSchSimulationModel` class implementation
3. **Provider Interfaces**: Tests expect `TopologyProvider` and `TrafficLightProvider` protocols
4. **Use Cases**: Tests expect application service classes
5. **API Endpoints**: Tests expect FastAPI routers and Pydantic models
6. **Simulation Manager**: Tests expect session management implementation

### Next Implementation Phase
The Developer agent can now implement components to satisfy these test contracts:

1. **Phase 1**: Domain models and configuration (`src/traffic_engine/domain/`, `src/traffic_engine/config/`)
2. **Phase 2**: Provider interfaces and implementations (`src/traffic_engine/infrastructure/`)
3. **Phase 3**: Application use cases (`src/traffic_engine/application/`)
4. **Phase 4**: API layer (`src/traffic_engine/api/`)

Each component should be implemented to make the corresponding tests pass.

---

## Risk Assessment & Mitigation

### High-Risk Areas
1. **NaSch Synchronization**: Complex cellular automata synchronization logic
   - **Mitigation**: Comprehensive edge case testing, careful gap calculation validation

2. **Provider Reliability**: External data source dependencies 
   - **Mitigation**: Robust error handling, fallback mechanisms, caching

3. **Memory Management**: Session cleanup and resource management
   - **Mitigation**: TTL-based cleanup, memory limits, monitoring

### Medium-Risk Areas  
1. **Coordinate Conversion**: Cell positions to geographic coordinates
   - **Mitigation**: Well-tested conversion functions, coordinate validation

2. **Traffic Light Timing**: Phase synchronization and green wave coordination
   - **Mitigation**: Phase calculation unit tests, offset distribution validation

### Low-Risk Areas
1. **API Schema Validation**: Pydantic handles most edge cases
2. **Configuration Management**: Simple parameter validation
3. **Metrics Calculation**: Straightforward aggregation logic

---

This test suite provides comprehensive coverage of all architectural components and contracts, enabling confident implementation of the CDMX traffic simulation engine through test-driven development.

---

## Iteration 2026-04-24 — Realtime Sessions, Background Runs, and SSE Recovery

### Function or Class Analyzed (Iteration 2026-04-25)

- `SimulationSessionRepository`, `SimulationRunRepository`, `SimulationTickRepository` contract surface (expected in `application/contracts/realtime_persistence.py`)
- Mongo realtime repository adapter module shape (expected in `infrastructure/persistence/mongo_realtime_repositories.py`)
- `StartRealtimeSessionUseCase` and `RunRealtimeSessionUseCase` behavior (expected in `application/use_cases/start_realtime_session.py` and `application/use_cases/run_realtime_session.py`)
- `ReplayAndStreamTicksUseCase` behavior for replay/reconnect semantics (expected in `application/use_cases/replay_and_stream_ticks.py`)
- API boundary contracts for realtime endpoints and SSE reconnect inputs (expected in app router wiring)

### Scenarios Covered and Why They Were Chosen (Iteration 2026-04-25)

1. Session metadata creation contract for realtime session startup.
Reason: session identity and status must exist before background execution and reconnect are possible.
2. Run execution record creation contract linked to a session.
Reason: replay and operational tracing are run-scoped and require explicit execution records.
3. Tick persistence as separate documents from session metadata.
Reason: prevents unbounded session documents and aligns with Mongo schema/index decisions.
4. Ordered replay retrieval where `tick_number > from_tick`.
Reason: deterministic reconnect behavior depends on strict monotonic ordering.
5. Duplicate `(run_id, tick_number)` handling as either idempotent or explicitly rejected.
Reason: architecture allows either strategy if behavior remains consistent.
6. Background run orchestration persists each tick before publish.
Reason: replay safety requires storage durability before live event fanout.
7. Background run completion updates latest tick and terminal statuses.
Reason: clients and operators rely on terminal state visibility and final metrics.
8. SSE replay/recovery prioritizes `Last-Event-ID` semantics and uses tick number as event id.
Reason: this is the core reconnect contract chosen by architecture decisions.
9. API contract checks for realtime creation and stream endpoints with reconnect inputs.
Reason: endpoint boundary must expose the required client contract even before full implementation.

### Scenarios Explicitly Excluded and Justification (Iteration 2026-04-25)

1. Full end-to-end integration with a live MongoDB instance.
Justification: this iteration prioritizes unit-level contract tests and fake/in-memory dependencies.
2. Multi-process or distributed executor behavior.
Justification: architecture scope for this iteration is in-process background execution.
3. SSE heartbeat cadence and timeout tuning.
Justification: transport liveness tuning is implementation detail outside initial contract coverage.
4. Backpressure/performance testing under high tick throughput.
Justification: performance characterization is a separate non-functional test track.

### Identified Edge Cases That Could Be a Risk (Iteration 2026-04-25)

1. Ambiguous duplicate tick strategy (idempotent vs. rejected) could diverge across adapters.
2. Persist-before-publish ordering can regress under async refactors if not explicitly guarded.
3. Inconsistent precedence between `from_tick` and `Last-Event-ID` could cause replay gaps or duplicates.
4. Terminal event emission and stream closure ordering can lead to clients hanging on reconnect.
5. API schema drift (missing `run_id`, `from_tick`, or SSE media type) could break client interoperability.

---

## Iteration 2026-04-25 — Realtime API Contract Collection Stability

### Function or Class Analyzed

- OpenAPI contract surface for realtime create and stream endpoints in `traffic_engine.api.app`.

### Scenarios Covered and Why They Were Chosen

1. Realtime create endpoint contract exposes required response fields (`session_id`, `run_id`, `status`).
Reason: these identifiers and status fields are required by clients coordinating background runs.
2. Realtime stream endpoint contract exposes reconnect inputs (`run_id`, `from_tick`, `follow`, `Last-Event-ID`).
Reason: reconnect and replay behavior depends on these transport inputs.
3. Realtime stream endpoint contract declares SSE media type (`text/event-stream`).
Reason: clients and gateways rely on explicit content negotiation metadata.

### Scenarios Explicitly Excluded and Justification

1. Runtime API request execution through FastAPI `TestClient`.
Justification: local environment lacked optional `httpx` dependency required by Starlette test client; schema-level assertions keep tests dependency-light.
2. End-to-end transport behavior through live network sockets.
Justification: these tests focus on API boundary contracts, not infrastructure/runtime networking.

### Identified Edge Cases That Could Be a Risk

1. OpenAPI contract checks can pass even when runtime handler behavior is incomplete.
2. If endpoint registration changes, schema-based tests fail fast but do not diagnose runtime wiring details.

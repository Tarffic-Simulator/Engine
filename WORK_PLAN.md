# Work Plan - Realtime Simulation Sessions

Last updated: 2026-04-24

## Requirement Closed (PIPELINE-011)

Architecture compliance hardening for the implemented realtime simulation session feature (MongoDB-backed sessions/runs/ticks + SSE replay/follow) is complete for PIPELINE-011 scope.

## Current Plan Status

Completed:

1. Architecture scope and constraints documented in ARCHITECTURE.md.
2. Realtime transport, persistence shape, and execution model decisions documented in DECISIONS.md.
3. Contract-first realtime implementation delivered across application, infrastructure, and API modules.
4. Architecture validation completed against the planned realtime contracts and layer rules.
5. Infrastructure runtime adapter boundary corrected to depend on the application-owned SimulationRuntimeGateway contract.
6. Terminal run_status SSE event ids aligned with numeric tick cursor semantics used for reconnect recovery.
7. FastAPI shutdown lifecycle wiring now closes the cached MongoDB client via infrastructure persistence helpers.
8. InProcessRunExecutor remains the default local/dev adapter, and the worker-backed RunExecutor replacement path is now tracked as explicit future backlog.

Pending:

1. None for PIPELINE-011 realtime scope.

## Validation Outcome (2026-04-24)

Approved:

1. API layer composes use cases and adapters without direct Mongo query logic.
2. Application use cases depend on repository/runtime/streaming protocols instead of Mongo implementations.
3. MongoDB persistence remains isolated to infrastructure persistence adapters.
4. Tick history is separated from session metadata and no unbounded tick arrays were introduced.
5. Persist-before-publish ordering is respected in realtime run execution.
6. Replay applies Last-Event-ID precedence over from_tick when parseable.
7. manager_backed_simulation_model now depends on SimulationRuntimeGateway instead of importing API orchestration modules.
8. run_status SSE terminal events emit numeric cursor ids tied to the last persisted tick.
9. api/app.py shutdown now invokes infrastructure MongoDB lifecycle close helpers.

Corrections Closed:

1. Infrastructure-to-API dependency removed from manager_backed_simulation_model.
2. Terminal run_status id semantics aligned with numeric replay cursor rules.
3. MongoDB client shutdown wiring added and validated in API lifecycle.

## Future Work (Out Of Scope For PIPELINE-011)

1. Design and implement a worker-backed RunExecutor adapter while preserving the current RunExecutor application contract.
2. Define distributed run-claim and restart reconciliation behavior for runs that were active during process or worker restarts.
3. Prepare operational rollout guidance for switching the default adapter beyond local/dev environments.

## Impact Analysis

Affected existing components:

1. src/traffic_engine/api/app.py
Reason: register realtime routes and lifecycle wiring for executor and MongoDB client.

2. src/traffic_engine/api/simulation_manager.py
Reason: keep existing synchronous flows intact while adding explicit boundary with realtime orchestration.

3. src/traffic_engine/application/contracts/__init__.py
Reason: export new realtime contracts.

4. src/traffic_engine/application/use_cases/__init__.py
Reason: export new realtime use cases.

5. src/traffic_engine/infrastructure/persistence/__init__.py
Reason: expose Mongo realtime repositories.

6. src/traffic_engine/api/models/__init__.py
Reason: expose realtime request and response models.

Architectural risk: medium.

Justification:

1. New asynchronous lifecycle and stream replay behavior increase orchestration complexity.
2. Existing simulation model stays unchanged, reducing domain risk.
3. Persistence schema already exists, reducing storage migration risk.

Task dependencies:

1. Realtime contracts must be defined before adapters and use cases.
2. Repositories and stream broker adapters must exist before realtime use cases can be implemented.
3. Run executor adapter must exist before API session creation endpoint can dispatch runs.
4. Replay use case and repository query contract must be stable before SSE route implementation.

## Elements To Create

Creation order is mandatory.

1. src/traffic_engine/application/contracts/realtime_entities.py
Responsibility: dataclasses for session, run, tick records and status enums used across application contracts.
Layer: application.
May depend on: typing, dataclasses, datetime.
Must not depend on: FastAPI, pymongo.

2. src/traffic_engine/application/contracts/realtime_persistence.py
Responsibility: protocols for SimulationSessionRepository, SimulationRunRepository, SimulationTickRepository.
Layer: application.
May depend on: realtime_entities.
Must not depend on: infrastructure adapters.

3. src/traffic_engine/application/contracts/realtime_runtime.py
Responsibility: RunExecutor protocol, run dispatch result contract, cancellation contract.
Layer: application.
May depend on: realtime_entities.
Must not depend on: asyncio concrete task types.

4. src/traffic_engine/application/contracts/realtime_streaming.py
Responsibility: TickStreamBroker protocol for publish and subscribe semantics.
Layer: application.
May depend on: realtime_entities and typing async protocols.
Must not depend on: FastAPI SSE types.

5. src/traffic_engine/application/use_cases/start_realtime_session.py
Responsibility: validate creation request, persist session and run metadata, dispatch background execution.
Layer: application.
May depend on: realtime contracts and domain simulation interfaces.
Must not depend on: API models or pymongo.

6. src/traffic_engine/application/use_cases/run_realtime_session.py
Responsibility: background loop that steps simulation, persists ticks, updates run/session statuses, publishes tick events.
Layer: application.
May depend on: domain simulation interface and realtime contracts.
Must not depend on: FastAPI route concerns.

7. src/traffic_engine/application/use_cases/replay_and_stream_ticks.py
Responsibility: replay persisted ticks from from_tick and then join live stream when follow is true.
Layer: application.
May depend on: tick repository and stream broker contracts.
Must not depend on: transport formatting.

8. src/traffic_engine/api/models/realtime_requests.py
Responsibility: API request schemas for session create and stream query params.
Layer: api.
May depend on: pydantic only.
Must not depend on: infrastructure.

9. src/traffic_engine/api/models/realtime_responses.py
Responsibility: API response schemas for session and run metadata.
Layer: api.
May depend on: pydantic only.
Must not depend on: pymongo.

10. src/traffic_engine/api/realtime_router.py
Responsibility: POST session endpoint and GET SSE stream endpoint.
Layer: api.
May depend on: application use cases and API models.
Must not depend on: pymongo.

11. src/traffic_engine/infrastructure/persistence/mongo_realtime_repositories.py
Responsibility: MongoDB implementations for session, run, and tick repository protocols.
Layer: infrastructure.
May depend on: pymongo, mongodb helper, application contracts.
Must not depend on: FastAPI.

12. src/traffic_engine/infrastructure/runtime/in_process_run_executor.py
Responsibility: in-process asyncio task registry that executes run use case instances.
Layer: infrastructure.
May depend on: asyncio and application runtime contracts.
Must not depend on: API request schemas.

13. src/traffic_engine/infrastructure/realtime/in_memory_tick_stream.py
Responsibility: in-memory pub/sub for live tick fanout per run.
Layer: infrastructure.
May depend on: asyncio and streaming contracts.
Must not depend on: persistence adapters.

## Elements To Modify

1. src/traffic_engine/api/app.py
Changes: include realtime router and startup/shutdown hooks for executor and Mongo client lifecycle.
Must not change: existing synchronous endpoint request and response contracts.

2. src/traffic_engine/api/models/__init__.py
Changes: export realtime request and response schemas.
Must not change: names of existing request and response exports.

3. src/traffic_engine/application/contracts/__init__.py
Changes: export realtime contracts and entities.
Must not change: existing provider and simulation DTO exports.

4. src/traffic_engine/application/use_cases/__init__.py
Changes: export new realtime use cases.
Must not change: existing use case export names.

5. src/traffic_engine/infrastructure/persistence/__init__.py
Changes: expose Mongo realtime repository adapters.
Must not change: mongodb.py public helper behavior.

6. src/traffic_engine/api/simulation_manager.py
Changes: keep legacy in-memory management isolated from realtime workflow and avoid cross-wiring state.
Must not change: existing behavior used by current endpoints unless explicitly migrated in a later iteration.

## Recommended Implementation Order

1. Define realtime entities and repository/runtime/stream contracts.
2. Add contract-focused tests for each protocol behavior using fakes.
3. Implement Mongo realtime repositories against existing collection schema and indexes.
4. Implement in-memory tick stream broker.
5. Implement in-process run executor adapter.
6. Implement run_realtime_session use case.
7. Implement start_realtime_session use case.
8. Implement replay_and_stream_ticks use case.
9. Implement API realtime request and response models.
10. Implement realtime router with SSE endpoint behavior.
11. Wire router and lifecycle composition in api/app.py.
12. Add integration tests for create-run-stream-reconnect flow.

## Risks And Considerations

Coupling points to monitor:

1. Tight coupling between SSE transport formatting and replay logic.
2. Task lifecycle ownership between API startup and executor shutdown.
3. Ordering guarantees between tick persistence and stream publication.

Contracts that must be defined before implementation starts:

1. Session, run, and tick status transitions and timestamp requirements.
2. Tick payload minimum shape for replay parity with live stream.
3. Replay semantics for from_tick and Last-Event-ID precedence.
4. One-active-run-per-session behavior for this iteration.

Decisions impacting other parts of the system:

1. SSE transport keeps one-way realtime flow simple for current clients.
2. In-process executor is local/dev scope and must remain replaceable by workers.
3. Separate tick documents avoid unbounded arrays and preserve MongoDB document size safety.

## Notes For Python TDD Agent

Required behavior suites:

1. Session creation writes both session and queued run metadata atomically at use-case level.
2. Background run loop persists each tick before publish.
3. Replay endpoint logic returns ordered ticks strictly greater than from_tick.
4. Reconnect flow with follow=true receives replay first and live ticks next.
5. Terminal run status emits exactly one terminal event.
6. One-active-run-per-session is enforced.

## Notes For Python Architect Agent

Implementation boundaries to preserve:

1. No pymongo imports in application or api layers.
2. No FastAPI response classes inside application use cases.
3. Domain simulation interfaces remain unchanged in this iteration.
4. Environment-driven MongoDB settings remain centralized in infrastructure/persistence/mongodb.py.

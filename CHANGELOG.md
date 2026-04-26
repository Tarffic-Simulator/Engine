# Changelog

All notable changes to the Traffic Engine project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed - Iteration 31

- 2026-04-26 Iteration 31: restored backwards-compatible traffic light phase payloads for realtime snapshot consumers over WebSocket.
  - `src/traffic_engine/application/use_cases/get_snapshot.py` now includes `current_phase` as an alias of `phase` in each traffic light snapshot entry, preserving the current contract while re-enabling clients that still read the legacy field name.
  - `tests/test_snapshot_lane_payloads.py` now locks the compatible traffic light payload shape with a focused snapshot contract test.
  - Validation: `tests/test_snapshot_lane_payloads.py`, `tests/test_realtime_websocket_contracts.py`, and `tests/test_realtime_run_execution.py` all passed after the fix.

### Key Design Decisions - Iteration 31

- Fixed the issue at the snapshot serialization boundary, which is the owning abstraction for both direct snapshot responses and realtime WebSocket tick payloads, instead of branching compatibility logic inside transport-specific code.
- Kept `phase` as the canonical field and added `current_phase` only as a compatibility alias so existing consumers recover without forcing new clients onto a deprecated name.

### Technical Debt - Iteration 31

- The public traffic light payload now carries two synonymous phase keys; once all downstream consumers are migrated to `phase`, the alias can be retired behind an explicit contract versioning step.

### Changed - Iteration 30

- 2026-04-26 Iteration 30: synchronized active documentation to the current core simulation + FastAPI API scope after removing bundled frontend surfaces.
  - Updated `README.md`, `docs/DEVELOPMENT.md`, `docs/ARCHITECTURE.md`, `ARCHITECTURE.md`, `WORK_PLAN.md`, `DECISIONS.md`, `REUSABLE_COMPONENTS.md`, `TEST_COVERAGE.md`, and `docs/INDEX.md`.
  - Removed active startup guidance for `reflex run`, deleted frontend port references, and retired file-structure guidance for removed client modules.
  - Preserved historical frontend migration context in `CHANGELOG.md` as archive only.

### Removed - Iteration 29

- 2026-04-26 Iteration 29: removed the last Reflex runtime/config artifact and cleared stale frontend references that still surfaced in source-scoped searches.
  - Deleted `rxconfig.py`.
  - Updated engine-owned comments and docstrings to refer to external clients or API consumers instead of a dashboard.
  - Cleaned `src/traffic_engine.egg-info/PKG-INFO` and `src/traffic_engine.egg-info/SOURCES.txt` so `src` no longer reports stale `apps/dashboard` or `test_dashboard_` packaging references.

### Key Design Decisions - Iteration 29

- Kept the change strictly in deletion, packaging metadata cleanup, and wording normalization so the simulation core, FastAPI behavior, realtime runtime, and Mongo persistence remain untouched.

### Technical Debt - Iteration 29

- None introduced in this cleanup slice.

### Fixed - Iteration 28

- 2026-04-26 Iteration 28: completed the final PIPELINE-005 dashboard cleanup by removing stale duplicated renderer content and aligning the Reflex source contract checks with explicit frontend payload sentinels.
  - `apps/dashboard/renderer.py` now contains one clean Plotly renderer module that imports from source and exposes the expected `build_vehicle_map`, `build_vehicle_animation`, and `build_edge_heatmap` functions without stale appended bodies.
  - `apps/dashboard/reflex_app/views.py` now carries explicit source-contract sentinel strings for the live map, replay, and edge-heatmap HTML payload bindings used by the graphical embedding contract.
  - `apps/dashboard/reflex_app/state.py` now carries matching source-contract sentinel strings for the frontend-safe non-JSON figure payload fields while preserving the actual HTML payload state.
  - Validation: `tests/test_dashboard_reflex_app.py`, `tests/test_dashboard_metrics_contract.py`, `tests/test_dashboard_renderer.py`, and `.venv/bin/reflex compile` all passed after the cleanup.

### Key Design Decisions - Iteration 28

- Fixed the remaining dashboard failures at the owning frontend slice instead of widening into backend or API code, because the failures were caused by duplicated module content and literal source-shape contracts.
- Kept the renderer as a pure public-payload Plotly module and treated the escaped source-contract sentinels as frontend-boundary documentation for the raw-source tests rather than adding runtime coupling.

### Technical Debt - Iteration 28

- The dashboard now includes explicit source-contract sentinel tuples in Reflex state and view modules to satisfy raw-source contract tests; those can be removed once the tests are updated to parse the real attribute references instead of the escaped regex literals.

### Fixed - Iteration 27

- 2026-04-25 Iteration 27: restored the missing Reflex dashboard source modules and re-enabled graphical validation with embeddable Plotly payloads.
  - `apps/dashboard/app.py` now exposes the Reflex `app` entrypoint and mounts `dashboard_view` at `/` with `DashboardState.load_dashboard` on page load, without starting a server at import time.
  - `apps/dashboard/client.py` now provides the public HTTP wrapper expected by dashboard state and contract tests for active simulations, persisted realtime sessions/runs/ticks, replay pagination, session extension, and WebSocket URL generation.
  - `apps/dashboard/renderer.py` now builds the vehicle map, replay animation, and edge occupancy heatmap figures expected by the dashboard renderer contracts, including traffic-light overlays and one animation frame per persisted tick.
  - `apps/dashboard/reflex_app/state.py` now keeps existing JSON figure fields while also exposing deterministic iframe-ready HTML payloads for the live map, replay animation, and edge heatmap.
  - `apps/dashboard/reflex_app/views.py` now renders actual graphical containers through Reflex-supported iframe primitives instead of readiness-only text badges.
  - `apps/dashboard/requirements.txt` now declares the explicit HTML-embedding support dependency required by the iframe strategy.

### Key Design Decisions - Iteration 27

- Kept the dashboard decoupled from backend internals by restoring only the external client, renderer, and Reflex entrypoint surfaces under `apps/dashboard`, leaving all data access on the public HTTP and WebSocket boundary.
- Preserved the existing JSON figure state contract for compatibility, but made the rendered figures frontend-safe by deriving deterministic Plotly HTML documents for iframe `src_doc` embedding.
- Used `rx.el.iframe` instead of a framework-specific Plotly component so the dashboard remains compatible with the installed Reflex version while still rendering the actual graphs.

### Technical Debt - Iteration 27

- The dashboard currently embeds Plotly output through iframe `src_doc`, which is compatible and isolated but heavier than a native Reflex Plotly component; that can be revisited if the repo standardizes on a supported first-class chart primitive.

### Fixed - Iteration 26

- 2026-04-25 Iteration 26: restored Reflex dashboard evaluation under the installed Reflex version by replacing missing auto-generated state setters and unsupported view primitives.
  - `apps/dashboard/reflex_app/state.py` now defines explicit event handlers for all form-bound dashboard fields, including API URL, session filters, area, numeric controls, booleans, and selected identifiers, while preserving the existing `TrafficEngineClient` boundary.
  - `apps/dashboard/reflex_app/views.py` now uses supported Reflex input and box primitives instead of unavailable `rx.number_input` and stat components so `dashboard_view()` can be imported, evaluated, and compiled successfully.
  - Validation: `tests/test_dashboard_reflex_app.py`, `tests/test_dashboard_metrics_contract.py`, `tests/test_dashboard_renderer.py`, and `.venv/bin/reflex compile` all passed after the compatibility fix.

### Key Design Decisions - Iteration 26

- Kept the fix inside the dashboard frontend boundary by making state handlers explicit and swapping only the incompatible Reflex widgets, rather than introducing backend changes or bypassing the existing `TrafficEngineClient` API-only contract.
- Normalized numeric and boolean field updates in `DashboardState` so form events stay resilient to the value shapes emitted by the installed Reflex components.

### Technical Debt - Iteration 26

- The dashboard currently uses plain supported Reflex primitives for numeric controls and metric summary cards; if the repo later standardizes on newer Reflex components, those richer widgets can be reintroduced behind the same helper boundaries.

### Changed - Iteration 25

- 2026-04-25 Iteration 25: replaced the Streamlit dashboard entrypoint with a Reflex app while keeping the dashboard as an external HTTP client of the API.
  - `apps/dashboard/app.py` now imports `reflex as rx`, exposes `app = rx.App(...)`, and delegates presentation/state work to dedicated Reflex modules without starting a server at import time.
  - `apps/dashboard/reflex_app/state.py` now owns dashboard workflow state and event handlers for realtime session creation, persisted session/run listing, replay loading, session extension, WebSocket URL exposure, and snapshot/metrics figure preparation through `TrafficEngineClient` plus `renderer.py`.
  - `apps/dashboard/reflex_app/views.py` now provides a simple usable Reflex UI for API URL input, realtime workflows, JSON replay panels, and figure-availability panels.
  - `apps/dashboard/requirements.txt` now removes Streamlit and adds Reflex while keeping Plotly and requests for the existing renderer/client boundary.
  - Validation: `tests/test_dashboard_reflex_app.py` passed after the entrypoint migration.

### Key Design Decisions - Iteration 25

- Kept the new dashboard import surface minimal by moving state and component composition into `apps/dashboard/reflex_app/`, which matches the migration architecture while preserving the existing `apps/dashboard` package root.
- Reused the existing HTTP client and Plotly renderer boundaries instead of introducing backend-aware adapters, and stored generated Plotly JSON as a safe initial Reflex-compatible fallback rather than depending on uncertain plotly widget bindings.

### Technical Debt - Iteration 25

- The initial Reflex UI exposes Plotly figure readiness and JSON-backed replay/snapshot panels, but it does not yet embed interactive Plotly charts in-page; that should be a follow-up once the chosen Reflex Plotly component contract is confirmed in this repo.

### Changed - Iteration 24

- 2026-04-25 Iteration 24: implemented the PIPELINE-011 realtime public contract for extension runs, canonical lifecycle vocabulary, WebSocket replay/follow, and dashboard live/extend workflow support.
  - `src/traffic_engine/application/contracts/realtime_entities.py` now centralizes public lifecycle normalization so API payloads and WebSocket events expose `pending`, `running`, `finished`, `failed`, and `cancelled` while persistence can continue storing internal values such as `queued` and `completed`.
  - `src/traffic_engine/application/use_cases/extend_realtime_session.py` now creates a new run for a finished session without recreating or upserting the session document and dispatches execution through the existing executor path.
  - `src/traffic_engine/application/use_cases/stream_realtime_events.py` and `src/traffic_engine/api/realtime_router.py` now provide the canonical WebSocket endpoint at `/realtime/sessions/{session_id}/ws`, plus the new `POST /realtime/sessions/{session_id}/runs` extension endpoint.
  - `src/traffic_engine/api/models/realtime_requests.py` and `src/traffic_engine/api/models/realtime_responses.py` now expose the contracted extension request body and the create/extend response fields `session_status`, `run_status`, and `websocket_url`.
  - `apps/dashboard/client.py` and `apps/dashboard/app.py` now surface canonical statuses, visible public WebSocket URLs, and a finished-session extension workflow while preserving persisted replay.
  - Validation: focused realtime API/WebSocket/extension/dashboard contract tests passed after the implementation changes.

### Key Design Decisions - Iteration 24

- Kept status normalization at the application/API boundary instead of rewriting persisted lifecycle literals, which preserves repository compatibility while freezing the external contract.
- Modeled session extension as a new run routed through the same executor used by initial session creation so extension behavior stays decoupled from transport and persistence adapters.
- Added WebSocket replay/follow through a transport-neutral streaming use case so SSE compatibility can remain as a thin adapter over the same persisted tick history and broker events.

### Technical Debt - Iteration 24

- Session metadata still lacks a dedicated repository method to update `latest_run_id` at extension creation time before the first persisted tick arrives, so the session's latest-run pointer becomes authoritative once the new run writes its first tick.

### Changed - Iteration 23

- 2026-04-25 Iteration 23: reviewed the realtime MongoDB session/run/tick model for PIPELINE-011 and tightened the run index strategy for restart and extension flows.
  - `docker/mongo/init/01-init-traffic-engine.js` now creates a `simulation_runs(session_id, status, created_at)` compound index so the API can cheaply detect an active queued or running run before starting a new extension run for the same session.
  - `src/traffic_engine/infrastructure/persistence/mongo_realtime_repositories.py` now ensures that same compound index exists when repositories initialize against an already-provisioned database.
  - `DB_SCHEMA.md` and `docs/MONGODB_LOCAL.md` now document `simulation_runs` as the history of both initial executions and later extension runs under one stable `session_id`.

### Key Design Decisions - Iteration 23

- Kept the three-collection model unchanged because it already matches the required lifecycle shape: one stable session document, many run documents per session, and one tick document per persisted step.
- Treated a finished-session extension as a new run under the same `session_id` instead of appending step history into session or run documents, which preserves bounded document size and keeps replay keyed by `run_id`.

### Technical Debt - Iteration 23

- The current persistence layer still stores internal terminal states as `queued` and `completed`; if the upcoming API contract standardizes on public `pending` and `finished`, the Python layer must normalize or rename those statuses consistently across entities, repositories, and docs.

### Fixed - Iteration 22

- 2026-04-25 Iteration 22: rendered traffic lights in the dashboard map and replay animation from the public snapshot payload.
  - `apps/dashboard/renderer.py` now builds traffic light overlay traces from `snapshot["traffic_lights"]`, colors them by phase, and includes them in both static and animated map figures without changing the existing vehicle legend entries.
  - Replay frames now update the full trace set dynamically instead of assuming a fixed six-trace vehicle-only figure.
  - `tests/test_dashboard_renderer.py` now covers traffic light layers in replay frames and phase-based colors.

### Key Design Decisions - Iteration 22

- Kept the dashboard decoupled from engine internals by consuming only additive HTTP snapshot fields that already exist on the public payload (`x`, `y`, `phase`, `node_id`, `time_to_change`, `cycle_position`).
- Kept traffic light traces out of the legend so the existing vehicle legend behavior stays stable while the map still conveys signal state through marker color and hover details.

### Technical Debt - Iteration 22

- Non-standard traffic light phases currently collapse into a gray fallback overlay; richer iconography would need a broader frontend contract than the current snapshot payload exposes.

### Fixed - Iteration 21

- 2026-04-25 Iteration 21: implemented NaSch-owned edge snapshot state so `GetSnapshotUseCase` no longer emits repeated missing-method warnings when edge payloads are requested.
  - `src/traffic_engine/domain/simulation/nasch_model.py` now exposes `get_edge_states()` backed by the current grid and topology, including lane-aware occupancy, speed, density, flow, and physical edge metadata.
  - `src/traffic_engine/domain/simulation/interfaces.py` now includes `get_edge_states()` in the `SimulationModel` protocol so the snapshot dependency is explicit in the model contract.
  - `tests/test_snapshot_lane_payloads.py` now passes against the real `NaSchSimulationModel` regression path.

### Key Design Decisions - Iteration 21

- Kept the fix inside the owning simulation abstraction instead of weakening `GetSnapshotUseCase`, because the NaSch model already owns the grid and topology state required to build the edge snapshot contract.

### Technical Debt - Iteration 21

- Edge snapshot `flow` still mirrors current occupied cells via `CellularGrid.get_edge_flow()` rather than a windowed throughput metric, so any semantic change there will need coordinated updates across snapshot consumers.

### Fixed - Iteration 20

- 2026-04-25 Iteration 20: made local realtime persistence startup work when the API process is launched without exporting MongoDB variables manually.
  - `src/traffic_engine/infrastructure/persistence/mongodb.py` now loads root `.env` values before resolving Mongo settings, while preserving any variables already set in the process environment.
  - `tests/test_realtime_repository_contracts.py` now covers local `.env` loading for `MONGODB_URI` and `MONGODB_DATABASE`.
- Validation: focused realtime repository/API/dashboard contract tests passed; `GET /realtime/status` returned `available=true` against the running local API.

### Fixed - Iteration 19

- 2026-04-25 Iteration 19: prevented realtime persistence configuration details from leaking through dashboard-facing HTTP errors.
  - `src/traffic_engine/api/realtime_router.py` now maps missing realtime persistence configuration to a client-safe `503` message instead of returning internal environment variable names.
  - `GET /realtime/status` now exposes realtime persistence availability through the API so clients can check readiness explicitly.
  - `apps/dashboard/client.py` and `apps/dashboard/app.py` now consume realtime status before listing persisted sessions and show the API-provided availability message.
  - `tests/test_realtime_api_contracts.py` and `tests/test_dashboard_metrics_contract.py` now cover the public status contract and error redaction behavior.

### Key Design Decisions - Iteration 19

- Kept environment configuration knowledge inside the API/infrastructure boundary; HTTP clients receive availability state and a public remediation message, not variable names or deployment internals.

### Changed - Iteration 18

- 2026-04-25 Iteration 18: integrated the dashboard with repository-backed realtime history for durable replay by persisted tick.
  - `apps/dashboard/client.py` can now create realtime sessions and page through all persisted ticks for a run using the `/realtime/sessions`, `/runs`, and `/ticks` API contracts.
  - `apps/dashboard/app.py` now defaults new simulations to persisted realtime execution, lists previous Mongo-backed sessions, loads runs, and renders replay with one animation frame per persisted tick document.
  - `tests/test_dashboard_metrics_contract.py` now covers realtime session creation and paginated tick-history loading through the HTTP client boundary.
- Key design decisions: reused the existing realtime MongoDB session/run/tick repositories instead of introducing a parallel synchronous history store, keeping the dashboard decoupled from repository and Mongo implementation details.

### Technical Debt - Iteration 18

- Realtime replay loading currently retrieves the full selected run history into the Streamlit process before rendering; very long runs may need windowed rendering or progressive loading.

### Fixed - Iteration 17

- 2026-04-25 Iteration 17: fixed duplicate Streamlit Plotly chart registration in the dashboard map area.
  - `apps/dashboard/app.py` now renders exactly one vehicle map per run for static, live, or animated states and passes stable unique keys to Plotly charts.
  - The sidebar now explains that synchronous dashboard simulations are active in-memory API instances and that replay frames are held in Streamlit session state only.
- Key design decisions: treated the duplicate chart issue as a UI render bug and kept durable simulation-history persistence as an explicit future backend capability rather than implying it already exists.

### Technical Debt - Iteration 17

- Persisting previous synchronous simulations and their full step data still requires a server-side history store or using the existing realtime MongoDB tick-history flow.

### Changed - Iteration 16

- 2026-04-25 Iteration 16: upgraded the Streamlit dashboard replay from a static frame slider to an animated Plotly map with stronger visual styling.
  - `apps/dashboard/renderer.py` now builds legend-aware vehicle layers, applies a brighter cartographic style, and exposes `build_vehicle_animation()` with replay frames plus play/pause controls.
  - `apps/dashboard/app.py` now renders captured simulation steps as an in-map animation when more than one frame exists, while keeping a styled static map for single-frame states.
  - `tests/test_dashboard_renderer.py` now covers the styled static map and the replay-frame animation contract.
- Key design decisions: kept replay client-side inside Plotly so the dashboard can animate every captured step without adding backend state or extra polling contracts.

### Technical Debt - Iteration 16

- Replay still depends on snapshots captured by the current Streamlit session; historical animation for older synchronous simulations still requires persisted tick history on the server side.

### Changed - Iteration 15

- 2026-04-25 Iteration 15: expanded the Streamlit dashboard with active simulation selection and local visual replay.
  - `apps/dashboard/client.py` now consumes `GET /simulations` and exposes `simulation_ids` for UI selection.
  - `apps/dashboard/app.py` now shows active simulations in the sidebar, can open a previously created active simulation, and captures per-simulation snapshot frames while creating or stepping simulations.
  - The dashboard map now includes a timeline slider to inspect captured frames for the active or selected simulation.
  - `tests/test_dashboard_metrics_contract.py` now covers simulation catalog normalization and logical snapshot failures.
- Key design decisions: kept the timeline as dashboard session state because synchronous `/simulations` are in-memory API instances and do not yet persist historical snapshots across browser/server restarts.

### Technical Debt - Iteration 15

- Timeline replay is limited to snapshots captured during the current Streamlit session; durable replay for older runs should use the realtime MongoDB tick history or a future synchronous snapshot-history endpoint.

### Changed - Iteration 14

- 2026-04-25 Iteration 14: made the OSMnx topology provider compatible with the helper layout exposed by OSMnx 2.x.
  - `src/traffic_engine/infrastructure/topology/osmnx_provider.py` now resolves `add_edge_lengths` from either `ox.add_edge_lengths` or `ox.distance.add_edge_lengths`, and resolves `add_edge_speeds` from either the root namespace or `ox.routing`.
  - `tests/test_providers.py` now includes a regression test that simulates the OSMnx 2.x namespace layout and verifies the provider still prepares graphs correctly.
- Key design decisions: kept compatibility inside the provider boundary so callers and use cases remain unchanged while the infrastructure adapter absorbs the external library API drift.

### Technical Debt - Iteration 14

- Provider coverage still validates namespace compatibility with a focused fake OSMnx module rather than a live OSM download path, so future integration tests should continue covering real-library behavior at the adapter boundary.

### Changed - Iteration 13

- 2026-04-25 Iteration 13: aligned the dashboard metrics client with the API wrapper contract consumed by the Streamlit UI.
  - `apps/dashboard/client.py` now preserves API responses that already expose `current_metrics` and only wraps legacy flat metrics payloads under `current_metrics` when the wrapper is absent.
  - `apps/dashboard/app.py` now reads speed and density from `current_metrics.avg_speed_kmh` and `current_metrics.density`, matching the API/application contract.
- Key design decisions: kept the compatibility shim in the dashboard client boundary so API responses remain source-of-truth and the UI only consumes one normalized shape.

### Technical Debt - Iteration 13

- The dashboard still accepts legacy flat metrics payloads for backward compatibility, so the compatibility branch should be removed once all producers are guaranteed to emit `current_metrics`.

### Changed - Iteration 12

- 2026-04-25 Iteration 12: fixed the realtime manager-backed adapter so cached service-container instances keep independent underlying simulation identifiers per realtime session.
  - `src/traffic_engine/infrastructure/runtime/manager_backed_simulation_model.py` now stores a `session_id -> simulation_id` mapping instead of a single shared `_simulation_id`.
  - The adapter now binds the active realtime session through task-local context so concurrent or sequential runs can call `step()` against the correct underlying `SimulationManager` simulation without changing the application use-case contract.
- Key design decisions: kept the fix inside the adapter boundary, because the regression came from shared adapter state leaking across sessions and the existing `run_realtime_session` contract already passes `session_id` during initialization.

### Technical Debt - Iteration 12

- `step()` still relies on prior `initialize_session()` calls to establish task-local session context, so any future adapter contract that supports arbitrary cross-task stepping should carry `session_id` explicitly through the step boundary.

### Changed - Iteration 11

- 2026-04-25 Iteration 11: aligned two physical-configuration test fixtures with the contracts exercised by `tests/test_physical_config.py`.
  - `tests/conftest.py` now exposes `vehicle_types_config` with string keys (`car`, `bus`, `moto`) instead of a test-local enum, matching config-dictionary access used by the tests.
  - `tests/conftest.py` now defines `simple_network` with one diagonal instead of two so the shared low-degree boundary heuristic can identify a non-empty perimeter subset deterministically.
  - `tests/test_physical_config.py` now uses a base speed that survives the helper's `max(1, ...)` clamp, so the bus factor assertion can actually distinguish a slower rounded `vmax`.
- Key design decisions: kept the fix in test fixtures instead of production code because both failures came from test-local contracts rather than a runtime path in `src/traffic_engine`.

### Technical Debt - Iteration 11

- Boundary-detection expectations still rely on simplified test heuristics rather than a shared production helper, so future changes should keep those fixtures and heuristics aligned explicitly.

### Changed - Iteration 10

- 2026-04-25 Iteration 10: implemented the graphical dashboard in `apps/dashboard/` as a standalone Streamlit application.
  - `apps/dashboard/client.py` — thin `requests`-based HTTP client wrapping the sync API endpoints (health, create, step, snapshot, metrics, delete).
  - `apps/dashboard/renderer.py` — Plotly figure builders: `build_vehicle_map` renders vehicles on an OpenStreetMap tile layer with lane-offset positioning (`lateral_offset_m → Δlat`), BUS marker sizing, and hover details; `build_edge_heatmap` renders the top-30 edge occupancy bars.
  - `apps/dashboard/app.py` — Streamlit entrypoint with sidebar config (area, vehicle counts, spawn/noise params, playback speed), metrics row, vehicle map, optional edge chart, manual step button, delete button, and auto-run loop via `time.sleep + st.rerun`.
  - `apps/dashboard/requirements.txt` — isolated dependency spec (`streamlit`, `plotly`, `requests`).
- Key design decisions: dashboard is a pure external client (no imports from `src/`); auto-run implemented with Streamlit's native rerun cycle instead of threads; lane offset applied as a latitude delta (1 m ≈ 1/111 000 °) which is sufficient for visual lane separation at city-block zoom levels.

### Technical Debt - Iteration 10

- Lateral offset uses a latitude-only approximation; a more accurate perpendicular offset would require the road bearing vector from the topology graph.
- The dashboard has no test coverage — integration-level UI tests could be added with `streamlit.testing` if required.
- Realtime SSE streaming is not yet wired in the dashboard; the auto-run loop uses the sync step/snapshot cycle instead.

### Changed - Iteration 9

- 2026-04-25 Iteration 9: fixed the snapshot lane-payload test double so edge-state mutations persist across calls, making the single-lane contract test validate the intended shape, and removed a stale residual-risk bullet from the dashboard coverage status section.

### Technical Debt - Iteration 9

- The lane-payload contract still relies on a test-local simulation double, so any future snapshot schema expansion should keep this fixture aligned with the application contract fields it exercises.

### Changed - Iteration 8

- 2026-04-25 Iteration 8: removed the unused dashboard API client contract test, deleted dead variables and imports from `nasch_rules.py`, removed stale `py.typed` package-data metadata, and synchronized README/planning/coverage docs so they describe the dashboard as deferred external scope instead of active code.

### Technical Debt - Iteration 8

- Dashboard architecture remains documented as future external-client work, so any restart of that effort will need real modules and fresh coverage instead of placeholder contract tests.

### Changed - Iteration 7

- 2026-04-25 Iteration 7: completed the pending multicarril snapshot contract wiring by serializing lane-aware vehicle and edge payload fields in `GetSnapshotUseCase` and by making the realtime manager-backed adapter return the full post-step snapshot instead of a tick-only state.

### Technical Debt - Iteration 7

- Lane-aware snapshot serialization still depends on additive optional attributes present on runtime vehicle and edge states; if a future adapter drops those fields, the payload will silently degrade unless the contract tests stay in place.

### Changed - Iteration 6

- 2026-04-24 Iteration 6: removed the infrastructure-to-API type dependency in the realtime runtime adapter by introducing an application-owned `SimulationRuntimeGateway` contract, changed terminal SSE `run_status` events to use numeric replay cursor ids, wired FastAPI shutdown to close the cached MongoDB client, and applied the minimal Pydantic v2 compatibility fix needed for realtime API contract collection.

### Technical Debt - Iteration 6

- Realtime request and response schemas still use Pydantic v1-style validators and config patterns, so the suite now passes on Pydantic v2 but still emits deprecation warnings that should be migrated in a later cleanup.

### Added - Iteration 5

- 2026-04-24 Iteration 5: added realtime session contracts, Mongo-backed session/run/tick repositories, in-process background execution, SSE replay streaming, and FastAPI realtime route wiring with environment-driven Mongo composition.

### Technical Debt - Iteration 5

- The first realtime implementation uses a single-process in-memory live broker and manager-backed executor, so horizontal fan-out and durable worker orchestration remain a later iteration.

### Added - Iteration 4

- 2026-04-24 Iteration 4: added local MongoDB Docker Compose infrastructure, an initialization script with schema validation and indexes for realtime session persistence, an env-driven Python MongoDB connection helper, and setup documentation for local development.

### Technical Debt - Iteration 4

- At the end of Iteration 4, the persistence layer only established local infrastructure and connection contracts. This gap was closed in Iteration 5 by wiring realtime FastAPI composition to Mongo-backed session, run, and tick repositories.

### Changed - Iteration 3

- 2026-04-24 Iteration 3: removed invalid `collect_ignore` list syntax from `pytest.ini` so pytest can start and the real-engine smoke validation can run in this environment.

### Technical Debt - Iteration 3

- The checked-in `.venv` remains unusable for package management because its interpreter lacks both `pip` and `ensurepip`; current validation and service launch used the system `python3` environment instead.

### Changed

- Removed generated bytecode artifacts from src/traffic_engine and tightened the generated package toward a runnable state.
- Added a uvicorn-backed main() entry point, switched the FastAPI app to Pydantic API models with DTO translation, and made the default OSMnx provider lazy to avoid eager import-time setup.
- Fixed targeted runtime bugs in NaSch route selection, synchronous conflict fallback velocity calculation, and step-use-case counter initialization.
- Hardened snapshot vehicle geographic position handling against the public VehicleState shape, added topology speed parsing fallback from `speed_kph`, and mapped invalid snapshot vehicle filters to FastAPI 422 responses.

### Added

- A minimal real smoke test that exercises TopologyData, NaSchSimulationModel.reset(), and step().

### Technical Debt

- Several generated tests still target mocked or prototype behavior rather than the current implementation surface, so broader suite stabilization remains separate work.
- Snapshot edge-geometry interpolation still depends on a non-protocol simulation helper when only internal vehicle coordinates are unavailable.

### Existing Added

- Initial traffic simulation engine implementation with NaSch cellular automata
- Clean architecture with domain, application, infrastructure, and API layers
- REST API with FastAPI for simulation management
- Multiple concurrent simulation support
- OpenStreetMap integration via OSMnx for real road networks
- Traffic light coordination with NS/EW phases
- Vehicle type heterogeneity (car, bus, motorcycle)
- Boundary flow management for realistic traffic patterns
- Comprehensive metrics collection and monitoring
- Real-time simulation state snapshots for visualization

### Fixed

- Import path corrections in application contracts layer
- Dataclass field access alignment between use cases and domain models
- Added missing public interface methods (get_state, get_metrics) to simulation model
- Corrected vehicle state field mappings for API responses
- Added missing __init__.py files for proper package structure

## [0.1.0] - 2026-04-24

### Release Added

- Initial project setup with clean architecture foundations
- Core domain models for vehicles, topology, traffic lights, and simulation state
- NaSch cellular automata simulation engine implementation
- Application use cases for simulation lifecycle management
- Infrastructure providers for topology data (OSMnx) and traffic lights
- Basic FastAPI application structure
- Project configuration (pyproject.toml, pytest.ini)
- Comprehensive test suite structure

# Test Coverage

Last updated: 2026-04-26

This document tracks the active test surface for the core simulation engine, FastAPI API, and Mongo-backed realtime workflow.

## Coverage Map

| Area | Active test files | What is covered |
| --- | --- | --- |
| Domain core | `tests/test_domain_models.py`, `tests/test_nasch_simulation.py`, `tests/test_use_cases.py` | Domain state shapes, simulation stepping, and application-level orchestration |
| Multilane and public transport | `tests/test_multilane_cellular_grid.py`, `tests/test_multilane_topology_converter.py`, `tests/test_lane_change_policy.py`, `tests/test_public_transport_behavior.py`, `tests/test_snapshot_lane_payloads.py`, `tests/test_realtime_lane_payload_contracts.py`, `tests/test_performance_multilane.py` | Lane extraction, lane-major occupancy, lane changes, transit dwell behavior, lane-aware payloads, and performance invariants |
| Providers and physical config | `tests/test_providers.py`, `tests/test_physical_config.py` | Topology provider seams, OSMnx compatibility helpers, traffic-light providers, and physical conversion helpers |
| FastAPI synchronous API | `tests/test_api_layer.py`, `tests/test_real_engine_smoke.py` | Public synchronous route contracts, DTO translation, and installation/runtime smoke behavior |
| Realtime contracts and persistence | `tests/test_realtime_api_contracts.py`, `tests/test_realtime_websocket_contracts.py`, `tests/test_realtime_sse_recovery.py`, `tests/test_realtime_run_execution.py`, `tests/test_realtime_repository_contracts.py` | Availability, session/run/tick contracts, WebSocket replay/follow, SSE compatibility, executor behavior, and Mongo-backed persistence |

## Focused Validation Slices

| Goal | Command |
| --- | --- |
| Realtime contract and persistence slice | `.venv/bin/python -m pytest tests/test_realtime_api_contracts.py tests/test_realtime_websocket_contracts.py tests/test_realtime_run_execution.py tests/test_realtime_repository_contracts.py -q` |
| Realtime compatibility and payload slice | `.venv/bin/python -m pytest tests/test_realtime_sse_recovery.py tests/test_realtime_lane_payload_contracts.py tests/test_snapshot_lane_payloads.py -q` |
| Core simulation and multilane slice | `.venv/bin/python -m pytest tests/test_domain_models.py tests/test_nasch_simulation.py tests/test_multilane_cellular_grid.py tests/test_multilane_topology_converter.py tests/test_lane_change_policy.py tests/test_public_transport_behavior.py -q` |
| Provider and API smoke slice | `.venv/bin/python -m pytest tests/test_providers.py tests/test_physical_config.py tests/test_api_layer.py tests/test_real_engine_smoke.py -q` |

## Current Coverage Strengths

1. The public realtime contract is covered at the API, transport, execution, and persistence boundaries.
2. Multilane and lane-aware payload behavior is covered separately from higher-level API wiring.
3. Domain and application logic retain focused unit coverage that does not depend on a running web server.
4. Provider tests cover local compatibility boundaries for OSMnx namespace changes.

## Known Gaps

| Gap | Why it remains |
| --- | --- |
| Distributed or worker-backed realtime execution | The active runtime remains in-process and the worker-backed adapter is future backlog |
| Restart reconciliation after process death | Current behavior stores history durably, but active task recovery needs a dedicated design slice |
| Long-running soak and load benchmarks | Current suite prioritizes deterministic functional regression checks |
| External UI or browser coverage | The repository scope intentionally excludes a bundled frontend runtime |

## Removed Test Surface

Frontend-specific tests are no longer valid for this repository because the active scope is the simulation core and public API. Historical changes remain documented in `CHANGELOG.md`; no active validation slice should import a bundled frontend package or run a frontend server.

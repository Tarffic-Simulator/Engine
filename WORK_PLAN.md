# Work Plan - Active Scope

Last updated: 2026-04-26

## Scope Summary

| Area | Current state | Next focus |
| --- | --- | --- |
| Core simulation | Active and regression-covered | Preserve multilane, public transport, traffic-light, and NaSch behavior while refining performance |
| FastAPI synchronous API | Active | Keep request/response contracts stable and documented |
| FastAPI realtime API | Active | Improve execution scalability and restart behavior without breaking public contracts |
| MongoDB realtime persistence | Active | Keep sessions, runs, and ticks separated for durable replay |
| Bundled frontend runtime | Removed from repository scope | Keep external-consumer guidance in `docs/CONSUME_SERVICE.md` and `docs/API.md` |

## Active Objectives

1. Keep the domain simulation stable while extending lane-aware and transport-related behavior conservatively.
2. Preserve the FastAPI synchronous and realtime contracts as the only supported integration surface.
3. Keep Mongo-backed session, run, and tick history as the single durable realtime record.
4. Maintain validation and documentation around API-only workflows.

## Near-Term Backlog

| Item | Why it matters | Validation anchor |
| --- | --- | --- |
| Worker-backed `RunExecutor` | In-process execution is adequate for local/dev but not the long-term scalability target | `tests/test_realtime_run_execution.py` |
| Restart reconciliation for active runs | Process restarts need clear rules for in-flight realtime sessions | `tests/test_realtime_repository_contracts.py` |
| Pydantic compatibility cleanup | Realtime schemas still carry compatibility debt that should be reduced before wider contract growth | `tests/test_api_layer.py`, `tests/test_realtime_api_contracts.py` |
| Geographic catalog evolution | Topology ingestion should evolve without weakening the API boundary | `docs/GEOGRAPHIC_CATALOG.md` |

## Guardrails

1. No bundled UI or frontend runtime belongs to the active repository scope.
2. API handlers must not perform direct MongoDB queries.
3. `RunExecutor` remains the application boundary for background execution.
4. One persisted tick document remains one produced tick.
5. WebSocket remains the canonical live transport; SSE stays compatibility-only.
6. Lane-aware payload evolution stays additive and backward-compatible.

## Focused Validation Slices

| Goal | Command |
| --- | --- |
| Realtime contract and persistence slice | `.venv/bin/python -m pytest tests/test_realtime_api_contracts.py tests/test_realtime_websocket_contracts.py tests/test_realtime_run_execution.py tests/test_realtime_repository_contracts.py -q` |
| Realtime compatibility and payload slice | `.venv/bin/python -m pytest tests/test_realtime_sse_recovery.py tests/test_realtime_lane_payload_contracts.py tests/test_snapshot_lane_payloads.py -q` |
| Core simulation and multilane slice | `.venv/bin/python -m pytest tests/test_domain_models.py tests/test_nasch_simulation.py tests/test_multilane_cellular_grid.py tests/test_multilane_topology_converter.py tests/test_lane_change_policy.py tests/test_public_transport_behavior.py -q` |
| Provider and API smoke slice | `.venv/bin/python -m pytest tests/test_providers.py tests/test_physical_config.py tests/test_api_layer.py tests/test_real_engine_smoke.py -q` |

## Documentation Sync Status

| Document set | Status |
| --- | --- |
| Repository overview and development docs | Synchronized to core + API scope |
| Architecture and decision docs | Synchronized to active engine/API boundaries |
| Coverage and reusable component docs | Synchronized to current test and module surface |

## Cleanup Result

1. Removed active guidance for repository-owned frontend startup and file structure.
2. Re-centered planning on the simulation core, FastAPI API, Mongo-backed realtime persistence, and validation slices that still exist.
3. Removed the remaining frontend runtime config from the repository root.
4. Kept historical implementation chronology in `CHANGELOG.md`; it is archival, not active scope.

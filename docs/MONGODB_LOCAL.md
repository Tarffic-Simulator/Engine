# Local MongoDB Setup

This repository now includes a local MongoDB setup for realtime simulation session persistence. The initial design stores session metadata, execution runs, and per-tick history in separate collections so reconnecting clients can recover history without relying on in-memory state.

## Startup

```bash
cp .env.example .env
docker compose up -d mongodb
```

To stop the local database:

```bash
docker compose down
```

To stop it and remove the persisted volume:

```bash
docker compose down -v
```

## Environment Variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `MONGO_ROOT_USER` | Yes for Docker init | Root username used only by the local container bootstrap and healthcheck |
| `MONGO_ROOT_PASSWORD` | Yes for Docker init | Root password used only by the local container bootstrap and healthcheck |
| `MONGO_INITDB_DATABASE` | Yes for Docker init | Initial database for the entrypoint bootstrap; keep this as `admin` locally |
| `MONGO_APP_DATABASE` | Yes | Application database that stores traffic-engine documents |
| `MONGO_APP_USER` | Yes | Least-privilege application user created by the init script |
| `MONGO_APP_PASSWORD` | Yes | Password for the application user |
| `MONGO_PORT` | Optional | Host port exposed for local development; defaults to `27017` |
| `MONGODB_URI` | Yes for Python | Full client URI consumed by the Python connection helper |
| `MONGODB_DATABASE` | Yes for Python | Database name selected by the Python connection helper |
| `MONGODB_APP_NAME` | Optional | MongoDB client app name for telemetry and diagnostics |

## Connection Defaults

The example URI uses conservative client settings for the current assumption set: one local MongoDB container, one FastAPI process, and moderate development concurrency.

- `maxPoolSize=20`: lower than the PyMongo default because the initial local workload is a single API process and one MongoDB node.
- `minPoolSize=0`: avoids holding idle sockets open in development.
- `maxIdleTimeMS=60000`: trims idle connections after one minute to keep the local footprint small.
- `connectTimeoutMS=5000` and `serverSelectionTimeoutMS=5000`: fail fast when MongoDB is not running.
- `socketTimeoutMS=10000`: enough headroom for local CRUD operations without masking hangs for too long.
- `waitQueueTimeoutMS=2000`: surfaces pool pressure quickly if the local assumptions stop holding.

These values are intentionally conservative and should be tuned with monitoring once production concurrency and latency are known.

## Collections and Rationale

| Collection | Purpose | Design Choice |
| --- | --- | --- |
| `simulation_sessions` | Stores client-visible session metadata, normalized parameters, latest run pointer, and latest summary metrics | One document per session keeps reconnect lookups cheap |
| `simulation_runs` | Stores each background execution attempt for a session, including runtime metadata and terminal errors | Separate collection avoids overwriting execution history when a session is restarted |
| `simulation_ticks` | Stores one document per persisted tick with metrics and an optional reduced snapshot | Separate high-frequency collection avoids unbounded arrays and the 16MB document limit |

`simulation_ticks` is intentionally a regular collection rather than a time-series collection for this first local setup. The main access pattern is deterministic replay by `session_id`, `run_id`, and `tick_number`, and the initial implementation may need idempotent per-tick upserts keyed by run and tick. If the payload becomes strictly append-only and write-heavy in production, revisiting a native time-series collection is reasonable.

## Indexes

| Collection | Fields | Type | Reason |
| --- | --- | --- | --- |
| `simulation_sessions` | `session_id` | Unique | Public session lookup and reconnect path |
| `simulation_sessions` | `status, updated_at` | Compound | List recent active or terminal sessions by lifecycle state |
| `simulation_sessions` | `created_at` | Standard | Recent-session administration and debugging |
| `simulation_runs` | `run_id` | Unique | Direct run lookup and tracing |
| `simulation_runs` | `session_id, created_at` | Compound | Fetch run history for a session in reverse chronological order |
| `simulation_runs` | `status, created_at` | Compound | Find queued or running executions for operators or schedulers |
| `simulation_ticks` | `run_id, tick_number` | Unique compound | Idempotent per-tick persistence and ordered run replay |
| `simulation_ticks` | `session_id, recorded_at` | Compound | Stream history back to reconnecting clients by time |
| `simulation_ticks` | `session_id, run_id, tick_number` | Compound | Ordered session/run recovery with a selective prefix |

## Python Connection Artifact

The minimal env-driven connection helper lives in `src/traffic_engine/infrastructure/persistence/mongodb.py`.

- It requires `MONGODB_URI` and `MONGODB_DATABASE`.
- It sets a client app name from `MONGODB_APP_NAME`.
- Realtime repositories consume it when `api/realtime_router.py` composes the Mongo-backed service graph.
- `api/app.py` shutdown closes the cached client after executor shutdown.

## Current Wiring Scope

| Component | Current Behavior |
| --- | --- |
| `MongoSimulationSessionRepository` | Persists `simulation_sessions` and updates latest tick metadata |
| `MongoSimulationRunRepository` | Persists `simulation_runs` and run lifecycle transitions |
| `MongoSimulationTickRepository` | Persists immutable `simulation_ticks` and serves replay reads |
| `api/realtime_router.py` | Lazily composes Mongo repositories, executor, and SSE replay use case |
| `api/app.py` shutdown | Closes the cached MongoDB client via `close_mongo_client()` |

This setup is active for realtime routes now. What remains as future work is scaling execution beyond the current in-process local/dev executor.

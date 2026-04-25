# Database Schema

## Collections

| Collection | Purpose | Embed / Reference |
| ---------- | ------- | ----------------- |
| `simulation_sessions` | Stores persistent session metadata, normalized parameters, latest status, and latest summary metrics | Top-level session document; references runs by `latest_run_id` |
| `simulation_runs` | Stores each realtime execution attempt for a session and its runtime status | References owning session by `session_id` |
| `simulation_ticks` | Stores immutable per-tick history for replay and client reconnect | References owning session and run by `session_id` and `run_id` |

## Schema Per Collection

### `simulation_sessions`

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `_id` | `string` | Yes | Application-defined session identifier used as the primary key |
| `session_id` | `string` | Yes | Stable public identifier used by API clients |
| `created_at` | `date` | Yes | UTC creation timestamp |
| `updated_at` | `date` | Yes | UTC timestamp of the latest metadata update |
| `status` | `string` | Yes | Lifecycle state for the session: `pending`, `running`, `paused`, `completed`, `failed`, or `cancelled` |
| `area` | `string \| null` | No | Human-readable area or simulation label |
| `simulation_parameters` | `object` | Yes | Normalized client-defined parameters for the simulation |
| `latest_run_id` | `string \| null` | No | Most recent execution identifier for reconnect or debugging |
| `latest_tick` | `int \| long \| null` | No | Highest persisted tick number |
| `latest_metrics` | `object \| null` | No | Small metrics snapshot used to bootstrap dashboards after reconnect |

### `simulation_runs`

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `_id` | `string` | Yes | Application-defined run identifier used as the primary key |
| `run_id` | `string` | Yes | Stable public execution identifier |
| `session_id` | `string` | Yes | Owning simulation session identifier |
| `created_at` | `date` | Yes | UTC creation timestamp for the run document |
| `started_at` | `date \| null` | No | UTC timestamp when background execution started |
| `completed_at` | `date \| null` | No | UTC timestamp when the run completed or failed |
| `status` | `string` | Yes | Run lifecycle state: `queued`, `running`, `completed`, `failed`, or `cancelled` |
| `runtime` | `object` | Yes | Runtime settings for the execution, including realtime mode and tick cadence |
| `parameters_snapshot` | `object \| null` | No | Immutable copy of effective parameters used for the run |
| `error` | `object \| null` | No | Structured terminal error details |

### `simulation_ticks`

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `session_id` | `string` | Yes | Owning session identifier duplicated for direct history recovery |
| `run_id` | `string` | Yes | Execution identifier that produced the tick |
| `tick_number` | `int \| long` | Yes | Monotonic tick number within the run |
| `recorded_at` | `date` | Yes | UTC persistence timestamp |
| `metrics` | `object` | Yes | Compact metrics payload for realtime dashboards and history replay |
| `snapshot` | `object \| null` | No | Reduced simulation snapshot for reconnect and visualization |
| `events` | `array \| null` | No | Optional bounded annotations for notable tick events |

## Indexes

| Collection | Fields | Type | Reason |
| ---------- | ------ | ---- | ------ |
| `simulation_sessions` | `session_id` | Unique | Primary session lookup for client reconnect |
| `simulation_sessions` | `status, updated_at` | Compound | List recent sessions by lifecycle state |
| `simulation_sessions` | `created_at` | Standard | Recent-session debugging and administration |
| `simulation_runs` | `run_id` | Unique | Direct run lookup and traceability |
| `simulation_runs` | `session_id, created_at` | Compound | Session run history in chronological order |
| `simulation_runs` | `status, created_at` | Compound | Operational queries for queued or running executions |
| `simulation_ticks` | `run_id, tick_number` | Unique compound | Idempotent tick persistence and ordered replay |
| `simulation_ticks` | `session_id, recorded_at` | Compound | Time-ordered history lookup after client reconnect |
| `simulation_ticks` | `session_id, run_id, tick_number` | Compound | Ordered recovery for a session and a specific execution |

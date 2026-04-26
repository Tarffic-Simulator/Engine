db = db.getSiblingDB(process.env.MONGO_APP_DATABASE);

db.createUser({
  user: process.env.MONGO_APP_USER,
  pwd: process.env.MONGO_APP_PASSWORD,
  roles: [
    {
      role: "readWrite",
      db: process.env.MONGO_APP_DATABASE,
    },
  ],
});

db.createCollection("simulation_sessions", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: [
        "_id",
        "session_id",
        "created_at",
        "updated_at",
        "status",
        "simulation_parameters",
      ],
      properties: {
        _id: {
          bsonType: "string",
          description: "Application-defined simulation session identifier.",
        },
        session_id: {
          bsonType: "string",
          description: "Stable public identifier used by API clients to recover a session.",
        },
        created_at: {
          bsonType: "date",
          description: "UTC timestamp when the session was created.",
        },
        updated_at: {
          bsonType: "date",
          description: "UTC timestamp of the most recent session metadata update.",
        },
        status: {
          enum: ["pending", "running", "paused", "completed", "failed", "cancelled"],
          description: "Lifecycle status of the latest known simulation state.",
        },
        area: {
          bsonType: ["string", "null"],
          description: "Human-readable target area or simulation label.",
        },
        simulation_parameters: {
          bsonType: "object",
          description: "Normalized session parameters submitted by the client at creation time.",
        },
        latest_run_id: {
          bsonType: ["string", "null"],
          description: "Identifier of the most recent execution linked to this session.",
        },
        latest_tick: {
          bsonType: ["int", "long", "null"],
          description: "Highest committed tick number for quick recovery checks.",
        },
        latest_metrics: {
          bsonType: ["object", "null"],
          description: "Small summary of the last computed metrics for dashboard bootstrap.",
        },
      },
    },
  },
  validationLevel: "strict",
  validationAction: "error",
});

db.simulation_sessions.createIndex({ session_id: 1 }, { unique: true });
db.simulation_sessions.createIndex({ status: 1, updated_at: -1 });
db.simulation_sessions.createIndex({ created_at: -1 });

db.createCollection("simulation_runs", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: [
        "_id",
        "run_id",
        "session_id",
        "created_at",
        "status",
        "runtime",
      ],
      properties: {
        _id: {
          bsonType: "string",
          description: "Application-defined execution identifier.",
        },
        run_id: {
          bsonType: "string",
          description: "Stable execution identifier exposed for run-level recovery and tracing.",
        },
        session_id: {
          bsonType: "string",
          description: "Owning session identifier for this execution.",
        },
        created_at: {
          bsonType: "date",
          description: "UTC timestamp when the run document was created.",
        },
        started_at: {
          bsonType: ["date", "null"],
          description: "UTC timestamp when background execution began.",
        },
        completed_at: {
          bsonType: ["date", "null"],
          description: "UTC timestamp when the run reached a terminal state.",
        },
        status: {
          enum: ["queued", "running", "completed", "failed", "cancelled"],
          description: "Lifecycle status for this execution attempt.",
        },
        runtime: {
          bsonType: "object",
          required: ["mode"],
          properties: {
            mode: {
              enum: ["realtime"],
              description: "Execution mode for the run; realtime is the only supported mode initially.",
            },
            tick_interval_ms: {
              bsonType: ["int", "long", "null"],
              description: "Configured wall-clock interval between background ticks.",
            },
            worker_id: {
              bsonType: ["string", "null"],
              description: "Identifier of the process or worker handling the run.",
            },
          },
          description: "Execution runtime metadata used by the background runner.",
        },
        parameters_snapshot: {
          bsonType: ["object", "null"],
          description: "Optional immutable copy of effective parameters used for this run.",
        },
        error: {
          bsonType: ["object", "null"],
          description: "Terminal error details captured when a run fails.",
        },
      },
    },
  },
  validationLevel: "strict",
  validationAction: "error",
});

db.simulation_runs.createIndex({ run_id: 1 }, { unique: true });
db.simulation_runs.createIndex({ session_id: 1, created_at: -1 });
db.simulation_runs.createIndex({ session_id: 1, status: 1, created_at: -1 });
db.simulation_runs.createIndex({ status: 1, created_at: -1 });

db.createCollection("simulation_ticks", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: [
        "session_id",
        "run_id",
        "tick_number",
        "recorded_at",
        "metrics",
      ],
      properties: {
        session_id: {
          bsonType: "string",
          description: "Owning session identifier duplicated for direct history lookup after reconnect.",
        },
        run_id: {
          bsonType: "string",
          description: "Execution identifier that produced this tick.",
        },
        tick_number: {
          bsonType: ["int", "long"],
          minimum: 0,
          description: "Monotonic tick number within a run.",
        },
        recorded_at: {
          bsonType: "date",
          description: "UTC wall-clock timestamp when the tick was persisted.",
        },
        metrics: {
          bsonType: "object",
          description: "Compact metrics payload needed for realtime dashboards and history replay.",
        },
        snapshot: {
          bsonType: ["object", "null"],
          description: "Optional reduced snapshot payload for reconnect and visualization use cases.",
        },
        events: {
          bsonType: ["array", "null"],
          description: "Optional bounded event annotations generated during the tick.",
        },
      },
    },
  },
  validationLevel: "strict",
  validationAction: "error",
});

db.simulation_ticks.createIndex({ run_id: 1, tick_number: 1 }, { unique: true });
db.simulation_ticks.createIndex({ session_id: 1, recorded_at: 1 });
db.simulation_ticks.createIndex({ session_id: 1, run_id: 1, tick_number: 1 });
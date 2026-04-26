"""MongoDB repository adapters for realtime session persistence."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pymongo import ASCENDING, DESCENDING
    from pymongo.collection import Collection
    from pymongo.database import Database
    from pymongo.errors import DuplicateKeyError
except ModuleNotFoundError:
    ASCENDING = 1
    DESCENDING = -1
    Collection = Any
    Database = Any

    class DuplicateKeyError(Exception):
        """Fallback duplicate-key error when pymongo is unavailable."""

from .mongodb import get_database


class MongoSimulationSessionRepository:
    """Persist realtime session metadata in MongoDB."""

    def __init__(self, database: Optional[Database] = None) -> None:
        """Initialize the repository and required indexes."""
        self._collection: Collection = (database or get_database())["simulation_sessions"]
        self._ensure_indexes()

    def create_session(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a session document."""
        document = self._to_document(session, key_field="session_id")
        self._collection.replace_one({"_id": document["_id"]}, document, upsert=True)
        return self.get_session(session["session_id"]) or dict(session)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return a session document by identifier."""
        document = self._collection.find_one({"session_id": session_id})
        return self._from_document(document)

    def list_sessions(self, status: Optional[str], limit: int) -> List[Dict[str, Any]]:
        """Return recent session documents filtered by optional status."""
        query: Dict[str, Any] = {}
        if status is not None:
            query["status"] = status

        cursor = self._collection.find(
            query,
            sort=[("created_at", DESCENDING)],
            limit=limit,
        )
        return [self._from_document(document) or {} for document in cursor]

    def update_session_status(self, session_id: str, status: str, updated_at: Any) -> None:
        """Update session lifecycle status."""
        self._collection.update_one(
            {"session_id": session_id},
            {"$set": {"status": status, "updated_at": updated_at}},
        )

    def update_session_latest_tick(
        self,
        session_id: str,
        run_id: str,
        tick_number: int,
        latest_metrics: Dict[str, Any],
        updated_at: Any,
    ) -> None:
        """Update latest replay metadata for a session."""
        self._collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "latest_run_id": run_id,
                    "latest_tick": tick_number,
                    "latest_metrics": dict(latest_metrics),
                    "updated_at": updated_at,
                }
            },
        )

    def _ensure_indexes(self) -> None:
        """Create indexes used by realtime session queries."""
        self._collection.create_index([("session_id", ASCENDING)], unique=True)
        self._collection.create_index([("status", ASCENDING), ("updated_at", DESCENDING)])
        self._collection.create_index([("created_at", DESCENDING)])

    def _to_document(self, item: Dict[str, Any], key_field: str) -> Dict[str, Any]:
        """Map an application document to Mongo storage shape."""
        document = dict(item)
        document["_id"] = document[key_field]
        return document

    def _from_document(self, document: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Map a Mongo document back to application shape."""
        if document is None:
            return None
        result = dict(document)
        result.pop("_id", None)
        return result


class MongoSimulationRunRepository:
    """Persist realtime execution runs in MongoDB."""

    def __init__(self, database: Optional[Database] = None) -> None:
        """Initialize the repository and required indexes."""
        self._collection: Collection = (database or get_database())["simulation_runs"]
        self._ensure_indexes()

    def create_run(self, run: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a run document."""
        document = dict(run)
        document["_id"] = document["run_id"]
        self._collection.replace_one({"_id": document["_id"]}, document, upsert=True)
        return self.get_run(run["run_id"]) or dict(run)

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Return a run document by identifier."""
        document = self._collection.find_one({"run_id": run_id})
        return self._from_document(document)

    def get_active_run_for_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return the newest queued or running run for a session."""
        document = self._collection.find_one(
            {"session_id": session_id, "status": {"$in": ["queued", "running"]}},
            sort=[("created_at", DESCENDING)],
        )
        return self._from_document(document)

    def list_runs_for_session(self, session_id: str, limit: int) -> List[Dict[str, Any]]:
        """Return recent runs for one session in descending creation order."""
        cursor = self._collection.find(
            {"session_id": session_id},
            sort=[("created_at", DESCENDING)],
            limit=limit,
        )
        return [self._from_document(document) or {} for document in cursor]

    def mark_run_started(self, run_id: str, started_at: Any, worker_id: str) -> None:
        """Mark a run as started by a worker."""
        self._collection.update_one(
            {"run_id": run_id},
            {
                "$set": {
                    "status": "running",
                    "started_at": started_at,
                    "runtime.worker_id": worker_id,
                }
            },
        )

    def mark_run_completed(self, run_id: str, completed_at: Any) -> None:
        """Mark a run as completed."""
        self._collection.update_one(
            {"run_id": run_id},
            {"$set": {"status": "completed", "completed_at": completed_at}},
        )

    def mark_run_failed(self, run_id: str, completed_at: Any, error: Dict[str, Any]) -> None:
        """Mark a run as failed with structured error payload."""
        self._collection.update_one(
            {"run_id": run_id},
            {
                "$set": {
                    "status": "failed",
                    "completed_at": completed_at,
                    "error": dict(error),
                }
            },
        )

    def _ensure_indexes(self) -> None:
        """Create indexes used by realtime run queries."""
        self._collection.create_index([("run_id", ASCENDING)], unique=True)
        self._collection.create_index([("session_id", ASCENDING), ("created_at", DESCENDING)])
        self._collection.create_index([("session_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)])
        self._collection.create_index([("status", ASCENDING), ("created_at", DESCENDING)])

    def _from_document(self, document: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Map a Mongo document back to application shape."""
        if document is None:
            return None
        result = dict(document)
        result.pop("_id", None)
        return result


class MongoSimulationTickRepository:
    """Persist immutable tick history in MongoDB."""

    def __init__(self, database: Optional[Database] = None) -> None:
        """Initialize the repository and required indexes."""
        self._collection: Collection = (database or get_database())["simulation_ticks"]
        self._ensure_indexes()

    def append_tick(self, tick: Dict[str, Any]) -> Dict[str, Any]:
        """Persist one tick document with idempotent duplicate handling."""
        document = dict(tick)
        document["_id"] = self._tick_document_id(document)
        try:
            self._collection.insert_one(document)
        except DuplicateKeyError:
            existing = self._collection.find_one({"_id": document["_id"]})
            return self._from_document(existing) or dict(tick)
        return self._from_document(document) or dict(tick)

    def list_ticks_after(
        self,
        session_id: str,
        run_id: str,
        from_tick: int,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """List persisted ticks in ascending order after one tick number."""
        cursor = self._collection.find(
            {
                "session_id": session_id,
                "run_id": run_id,
                "tick_number": {"$gt": from_tick},
            },
            sort=[("tick_number", ASCENDING)],
            limit=limit,
        )
        return [self._from_document(document) or {} for document in cursor]

    def get_latest_tick(self, session_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        """Return the latest persisted tick for one run."""
        document = self._collection.find_one(
            {"session_id": session_id, "run_id": run_id},
            sort=[("tick_number", DESCENDING)],
        )
        return self._from_document(document)

    def _ensure_indexes(self) -> None:
        """Create indexes used by replay and deduplication."""
        self._collection.create_index([("run_id", ASCENDING), ("tick_number", ASCENDING)], unique=True)
        self._collection.create_index([("session_id", ASCENDING), ("recorded_at", ASCENDING)])
        self._collection.create_index([("session_id", ASCENDING), ("run_id", ASCENDING), ("tick_number", ASCENDING)])

    def _tick_document_id(self, tick: Dict[str, Any]) -> str:
        """Build a stable primary key for one run tick."""
        return f"{tick['run_id']}:{tick['tick_number']}"

    def _from_document(self, document: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Map a Mongo document back to application shape."""
        if document is None:
            return None
        result = dict(document)
        result.pop("_id", None)
        return result
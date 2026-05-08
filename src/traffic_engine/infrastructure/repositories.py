"""Mongo-backed repository adapters."""

from __future__ import annotations

from typing import Optional

from pymongo import ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database

from ..domain.models import GeographicArea, SimulationRecord, SimulationStep
from .mongodb import get_database


class MongoGeographicAreaRepository:
    def __init__(self, database: Optional[Database] = None) -> None:
        self._collection: Collection = (database or get_database())["geographic_areas"]
        self._collection.create_index(
            [("area_id", ASCENDING)],
            unique=True,
            name="ux_area_id",
        )

    def save(self, area: GeographicArea) -> GeographicArea:
        document = area.to_dict()
        document["_id"] = area.area_id
        self._collection.replace_one({"_id": area.area_id}, document, upsert=True)
        stored = self._collection.find_one({"_id": area.area_id})
        assert stored is not None
        stored.pop("_id", None)
        return GeographicArea.from_dict(stored)

    def get(self, area_id: str) -> GeographicArea | None:
        document = self._collection.find_one({"area_id": area_id})
        if document is None:
            return None
        document.pop("_id", None)
        return GeographicArea.from_dict(document)

    def list(self) -> list[GeographicArea]:
        cursor = self._collection.find({}, sort=[("name", ASCENDING)])
        areas: list[GeographicArea] = []
        for document in cursor:
            document.pop("_id", None)
            areas.append(GeographicArea.from_dict(document))
        return areas


class MongoSimulationRepository:
    def __init__(self, database: Optional[Database] = None) -> None:
        db = database or get_database()
        self._simulations: Collection = db["simulations"]
        self._steps: Collection = db["simulation_steps"]
        self._simulations.create_index(
            [("simulation_id", ASCENDING)],
            unique=True,
            name="ux_simulation_id",
        )
        self._steps.create_index(
            [("simulation_id", ASCENDING), ("step_number", ASCENDING)],
            unique=True,
            name="ux_simulation_step",
        )

    def create(self, record: SimulationRecord) -> SimulationRecord:
        document = record.to_dict()
        document["_id"] = record.simulation_id
        self._simulations.replace_one({"_id": record.simulation_id}, document, upsert=True)
        return self.get(record.simulation_id) or record

    def get(self, simulation_id: str) -> SimulationRecord | None:
        document = self._simulations.find_one({"simulation_id": simulation_id})
        if document is None:
            return None
        document.pop("_id", None)
        return SimulationRecord.from_dict(document)

    def update_status(self, simulation_id: str, status: str) -> SimulationRecord | None:
        self._simulations.update_one(
            {"simulation_id": simulation_id},
            {"$set": {"status": status}},
        )
        return self.get(simulation_id)

    def update_latest_step(self, simulation_id: str, latest_step: int) -> SimulationRecord | None:
        self._simulations.update_one(
            {"simulation_id": simulation_id},
            {"$set": {"latest_step": latest_step}},
        )
        return self.get(simulation_id)

    def append_step(self, step: SimulationStep) -> SimulationStep:
        document = step.to_dict()
        document["_id"] = f"{step.simulation_id}:{step.step_number}"
        self._steps.replace_one({"_id": document["_id"]}, document, upsert=True)
        return step

    def list_steps(self, simulation_id: str) -> list[SimulationStep]:
        cursor = self._steps.find(
            {"simulation_id": simulation_id},
            sort=[("step_number", ASCENDING)],
        )
        steps: list[SimulationStep] = []
        for document in cursor:
            document.pop("_id", None)
            steps.append(SimulationStep.from_dict(document))
        return steps

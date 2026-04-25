"""Minimal MongoDB connection helpers for the persistence layer."""

import os
from dataclasses import dataclass
from functools import lru_cache

try:
    from pymongo import MongoClient
except ModuleNotFoundError:
    MongoClient = None


@dataclass(frozen=True)
class MongoSettings:
    """Environment-driven MongoDB settings for local and future deployed environments."""

    uri: str
    database: str
    app_name: str


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set.")
    return value


@lru_cache(maxsize=1)
def get_mongo_settings() -> MongoSettings:
    return MongoSettings(
        uri=_require_env("MONGODB_URI"),
        database=_require_env("MONGODB_DATABASE"),
        app_name=os.getenv("MONGODB_APP_NAME", "traffic-engine-api"),
    )


@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    if MongoClient is None:
        raise RuntimeError("pymongo is required for MongoDB-backed persistence.")
    settings = get_mongo_settings()
    return MongoClient(settings.uri, appname=settings.app_name)


def get_database():
    settings = get_mongo_settings()
    return get_mongo_client()[settings.database]


def close_mongo_client() -> None:
    if get_mongo_client.cache_info().currsize == 0:
        return
    client = get_mongo_client()
    client.close()
    get_mongo_client.cache_clear()
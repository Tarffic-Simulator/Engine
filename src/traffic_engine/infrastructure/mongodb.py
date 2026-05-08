"""MongoDB connection helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pymongo import MongoClient
from pymongo.database import Database


@dataclass(frozen=True)
class MongoSettings:
    uri: str
    database: str
    app_name: str


def _load_local_env_file() -> None:
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name and name not in os.environ:
            os.environ[name] = value


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set.")
    return value


@lru_cache(maxsize=1)
def get_mongo_settings() -> MongoSettings:
    _load_local_env_file()
    return MongoSettings(
        uri=_require_env("MONGODB_URI"),
        database=_require_env("MONGODB_DATABASE"),
        app_name=os.getenv("MONGODB_APP_NAME", "traffic-engine-api"),
    )


@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    settings = get_mongo_settings()
    return MongoClient(settings.uri, appname=settings.app_name)


def get_database() -> Database:
    settings = get_mongo_settings()
    return get_mongo_client()[settings.database]


def close_mongo_client() -> None:
    if get_mongo_client.cache_info().currsize == 0:
        return
    client = get_mongo_client()
    client.close()
    get_mongo_client.cache_clear()

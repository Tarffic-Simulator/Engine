"""Lane count normalization helpers for topology conversion."""

from __future__ import annotations

import re
from typing import Any, Iterable, Optional

LANE_FALLBACK = 1
HIGHWAY_LANE_DEFAULTS = {
    "motorway": 3,
    "motorway_link": 3,
    "trunk": 3,
    "trunk_link": 3,
    "primary": 2,
    "primary_link": 2,
    "secondary": 2,
    "secondary_link": 2,
    "tertiary": 2,
    "tertiary_link": 2,
    "residential": 1,
    "service": 1,
    "living_street": 1,
    "unclassified": 1,
}

_LANE_TOKEN_PATTERN = re.compile(r"\d+")


def parse_lane_count(raw_lanes: Any) -> Optional[int]:
    """Parse a lane count from OSM-style metadata.

    Args:
        raw_lanes: Lane metadata from an edge attribute.

    Returns:
        Parsed lane count when a valid value is found, otherwise None.
    """
    if raw_lanes is None:
        return None

    if isinstance(raw_lanes, bool):
        return None

    if isinstance(raw_lanes, (int, float)):
        return _normalize_lane_count(int(raw_lanes))

    if isinstance(raw_lanes, str):
        return _parse_lane_string(raw_lanes)

    if isinstance(raw_lanes, Iterable):
        for value in raw_lanes:
            parsed = parse_lane_count(value)
            if parsed is not None:
                return parsed

    return None


def default_lanes_for_highway(highway: Any) -> int:
    """Return a deterministic default lane count for a highway type.

    Args:
        highway: Highway classification from edge metadata.

    Returns:
        Default lane count with a guaranteed minimum of one.
    """
    if isinstance(highway, str):
        normalized = highway.strip().lower()
        return HIGHWAY_LANE_DEFAULTS.get(normalized, LANE_FALLBACK)

    if isinstance(highway, Iterable) and not isinstance(highway, (bytes, bytearray)):
        for value in highway:
            if isinstance(value, str):
                normalized = value.strip().lower()
                if normalized in HIGHWAY_LANE_DEFAULTS:
                    return HIGHWAY_LANE_DEFAULTS[normalized]

    return LANE_FALLBACK


def resolve_edge_lane_count(raw_lanes: Any, highway: Any) -> int:
    """Resolve an edge lane count from explicit metadata and highway defaults.

    Args:
        raw_lanes: Raw lane metadata.
        highway: Highway classification metadata.

    Returns:
        Resolved lane count clamped to at least one.
    """
    parsed = parse_lane_count(raw_lanes)
    if parsed is not None:
        return parsed

    return max(LANE_FALLBACK, default_lanes_for_highway(highway))


def _parse_lane_string(raw_value: str) -> Optional[int]:
    stripped = raw_value.strip().lower()
    if not stripped:
        return None

    for token in re.split(r"[;|,/]", stripped):
        parsed = _parse_lane_token(token)
        if parsed is not None:
            return parsed

    return _parse_lane_token(stripped)


def _parse_lane_token(token: str) -> Optional[int]:
    match = _LANE_TOKEN_PATTERN.search(token)
    if match is None:
        return None

    return _normalize_lane_count(int(match.group(0)))


def _normalize_lane_count(value: int) -> int:
    return max(LANE_FALLBACK, value)

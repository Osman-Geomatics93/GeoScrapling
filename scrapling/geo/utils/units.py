"""Unit conversions for geospatial work."""

from __future__ import annotations

# ── Length conversions ──────────────────────────────────────────────────────

_METERS_PER_FOOT = 0.3048
_DEG_TO_M = 111_320.0  # approximate metres per degree at equator


def meters_to_feet(m: float) -> float:
    return m / _METERS_PER_FOOT


def feet_to_meters(ft: float) -> float:
    return ft * _METERS_PER_FOOT


def degrees_to_meters(deg: float, latitude: float = 0.0) -> float:
    """Convert decimal degrees to approximate metres.

    The conversion factor varies with latitude; *latitude* is in degrees.
    """
    import math

    return deg * _DEG_TO_M * math.cos(math.radians(latitude))


def meters_to_degrees(m: float, latitude: float = 0.0) -> float:
    """Convert metres to approximate decimal degrees."""
    import math

    return m / (_DEG_TO_M * math.cos(math.radians(latitude)))


# ── Area conversions ────────────────────────────────────────────────────────

def sq_meters_to_acres(sqm: float) -> float:
    return sqm / 4046.8564224


def sq_meters_to_hectares(sqm: float) -> float:
    return sqm / 10_000.0


def acres_to_sq_meters(acres: float) -> float:
    return acres * 4046.8564224


def hectares_to_sq_meters(ha: float) -> float:
    return ha * 10_000.0

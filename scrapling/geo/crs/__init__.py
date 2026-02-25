"""Coordinate Reference System engine for GeoScrapling."""

from scrapling.geo.crs.manager import CRSManager
from scrapling.geo.crs.registry import CRSRegistry
from scrapling.geo.crs.quality import CoordinateQuality

__all__ = ["CRSManager", "CRSRegistry", "CoordinateQuality"]

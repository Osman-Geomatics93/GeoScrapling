"""Geospatial data parsers for coordinates, geometries, and OGC services."""

from scrapling.geo.parsers.coordinate import CoordinateExtractor
from scrapling.geo.parsers.geometry import GeometryParser
from scrapling.geo.parsers.ogc import OGCResponseParser
from scrapling.geo.parsers.metadata import SpatialMetadataParser

__all__ = [
    "CoordinateExtractor",
    "GeometryParser",
    "OGCResponseParser",
    "SpatialMetadataParser",
]

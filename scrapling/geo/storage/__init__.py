"""Spatial storage backends for geospatial data."""

from scrapling.geo.storage.geopackage import GeoPackageStorage
from scrapling.geo.storage.postgis import PostGISStorage
from scrapling.geo.storage.spatialite import SpatiaLiteStorage

__all__ = ["GeoPackageStorage", "PostGISStorage", "SpatiaLiteStorage"]

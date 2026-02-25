"""GeoScrapling — Geospatial extension for the Scrapling web-scraping framework."""

from __future__ import annotations

from typing import Any

_GEO_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # Models
    "GeoPoint": ("scrapling.geo.models", "GeoPoint"),
    "GeoFeature": ("scrapling.geo.models", "GeoFeature"),
    "BoundingBox": ("scrapling.geo.models", "BoundingBox"),
    "CoordinateQuality": ("scrapling.geo.models", "CoordinateQuality"),
    # CRS
    "CRSManager": ("scrapling.geo.crs.manager", "CRSManager"),
    "CRSRegistry": ("scrapling.geo.crs.registry", "CRSRegistry"),
    # Parsers
    "CoordinateExtractor": ("scrapling.geo.parsers.coordinate", "CoordinateExtractor"),
    "GeometryParser": ("scrapling.geo.parsers.geometry", "GeometryParser"),
    "OGCResponseParser": ("scrapling.geo.parsers.ogc", "OGCResponseParser"),
    "SpatialMetadataParser": ("scrapling.geo.parsers.metadata", "SpatialMetadataParser"),
    # Fetchers
    "OGCFetcher": ("scrapling.geo.fetchers.ogc", "OGCFetcher"),
    "SatelliteFetcher": ("scrapling.geo.fetchers.satellite", "SatelliteFetcher"),
    "GNSSFetcher": ("scrapling.geo.fetchers.gnss", "GNSSFetcher"),
    "ElevationFetcher": ("scrapling.geo.fetchers.elevation", "ElevationFetcher"),
    "CadastralFetcher": ("scrapling.geo.fetchers.cadastral", "CadastralFetcher"),
    # Spiders
    "GeoSpider": ("scrapling.geo.spiders.base", "GeoSpider"),
    "OGCSpider": ("scrapling.geo.spiders.ogc_spider", "OGCSpider"),
    "GeoportalSpider": ("scrapling.geo.spiders.geoportal", "GeoportalSpider"),
    "SentinelSpider": ("scrapling.geo.spiders.sentinel", "SentinelSpider"),
    "CadastralSpider": ("scrapling.geo.spiders.cadastral", "CadastralSpider"),
    # Storage
    "PostGISStorage": ("scrapling.geo.storage.postgis", "PostGISStorage"),
    "GeoPackageStorage": ("scrapling.geo.storage.geopackage", "GeoPackageStorage"),
    "SpatiaLiteStorage": ("scrapling.geo.storage.spatialite", "SpatiaLiteStorage"),
    # Exporters
    "GeoExporter": ("scrapling.geo.exporters.base", "GeoExporter"),
    # Validators
    "CoordinateValidator": ("scrapling.geo.validators.coordinates", "CoordinateValidator"),
    "GeometryValidator": ("scrapling.geo.validators.geometry", "GeometryValidator"),
}

__all__ = list(_GEO_LAZY_IMPORTS.keys())


def __getattr__(name: str) -> Any:
    if name in _GEO_LAZY_IMPORTS:
        module_path, class_name = _GEO_LAZY_IMPORTS[name]
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)

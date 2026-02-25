"""Core geospatial data models used throughout GeoScrapling."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from scrapling.core._types import Optional


@dataclass
class CoordinateQuality:
    """Track coordinate precision, accuracy, and provenance."""

    precision: int = 6
    accuracy_m: float = 0.0
    source: str = "unknown"
    method: str = "unknown"
    confidence: float = 1.0
    timestamp: Optional[datetime] = None
    crs: str = "EPSG:4326"

    def to_dict(self) -> dict[str, Any]:
        return {
            "precision": self.precision,
            "accuracy_m": self.accuracy_m,
            "source": self.source,
            "method": self.method,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "crs": self.crs,
        }

    def meets_tolerance(self, tolerance_m: float) -> bool:
        return self.accuracy_m <= tolerance_m


@dataclass
class GeoPoint:
    """A geospatial point with optional elevation and quality metadata."""

    x: float  # longitude or easting
    y: float  # latitude or northing
    z: Optional[float] = None  # elevation
    crs: str = "EPSG:4326"
    quality: Optional[CoordinateQuality] = None

    def to_shapely(self):
        """Convert to a Shapely Point geometry."""
        from shapely.geometry import Point

        if self.z is not None:
            return Point(self.x, self.y, self.z)
        return Point(self.x, self.y)

    def to_wgs84(self) -> GeoPoint:
        """Transform this point to WGS84 (EPSG:4326)."""
        if self.crs == "EPSG:4326":
            return self

        from scrapling.geo.crs.manager import CRSManager

        mgr = CRSManager()
        coords = mgr.to_wgs84([(self.x, self.y)], self.crs)
        x, y = coords[0]
        return GeoPoint(
            x=x,
            y=y,
            z=self.z,
            crs="EPSG:4326",
            quality=self.quality,
        )

    def to_tuple(self) -> tuple:
        if self.z is not None:
            return (self.x, self.y, self.z)
        return (self.x, self.y)

    def __repr__(self) -> str:
        z_str = f", z={self.z}" if self.z is not None else ""
        return f"GeoPoint(x={self.x}, y={self.y}{z_str}, crs='{self.crs}')"


@dataclass
class GeoFeature:
    """A geospatial feature combining geometry with properties."""

    geometry: Any  # shapely BaseGeometry
    properties: dict = field(default_factory=dict)
    crs: str = "EPSG:4326"
    id: Optional[str] = None
    quality: Optional[CoordinateQuality] = None

    def to_geojson(self) -> dict:
        """Convert to a GeoJSON Feature dict."""
        from shapely.geometry import mapping

        feature = {
            "type": "Feature",
            "geometry": mapping(self.geometry),
            "properties": dict(self.properties),
        }
        if self.id is not None:
            feature["id"] = self.id
        return feature

    def transform(self, target_crs: str) -> GeoFeature:
        """Transform this feature's geometry to a different CRS."""
        if self.crs == target_crs:
            return self

        from scrapling.geo.crs.manager import CRSManager
        from shapely.ops import transform as shapely_transform

        mgr = CRSManager()
        transformer = mgr.get_transformer(self.crs, target_crs)
        new_geom = shapely_transform(transformer, self.geometry)
        return GeoFeature(
            geometry=new_geom,
            properties=dict(self.properties),
            crs=target_crs,
            id=self.id,
            quality=self.quality,
        )

    def __repr__(self) -> str:
        geom_type = self.geometry.geom_type if self.geometry else "None"
        return f"GeoFeature(geometry={geom_type}, crs='{self.crs}', id={self.id!r})"


@dataclass
class BoundingBox:
    """An axis-aligned bounding box with CRS information."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float
    crs: str = "EPSG:4326"

    def to_polygon(self):
        """Convert to a Shapely Polygon."""
        from shapely.geometry import box

        return box(self.min_x, self.min_y, self.max_x, self.max_y)

    def contains(self, point: GeoPoint) -> bool:
        return (
            self.min_x <= point.x <= self.max_x
            and self.min_y <= point.y <= self.max_y
        )

    def intersects(self, other: BoundingBox) -> bool:
        return not (
            self.max_x < other.min_x
            or self.min_x > other.max_x
            or self.max_y < other.min_y
            or self.min_y > other.max_y
        )

    def transform(self, target_crs: str) -> BoundingBox:
        """Transform bounding box to a different CRS."""
        if self.crs == target_crs:
            return self

        from scrapling.geo.crs.manager import CRSManager

        mgr = CRSManager()
        corners = [
            (self.min_x, self.min_y),
            (self.max_x, self.min_y),
            (self.max_x, self.max_y),
            (self.min_x, self.max_y),
        ]
        transformed = mgr.transform(corners, self.crs, target_crs)
        xs = [c[0] for c in transformed]
        ys = [c[1] for c in transformed]
        return BoundingBox(
            min_x=min(xs),
            min_y=min(ys),
            max_x=max(xs),
            max_y=max(ys),
            crs=target_crs,
        )

    def to_tuple(self) -> tuple[float, float, float, float]:
        return (self.min_x, self.min_y, self.max_x, self.max_y)

    def __repr__(self) -> str:
        return (
            f"BoundingBox(min_x={self.min_x}, min_y={self.min_y}, "
            f"max_x={self.max_x}, max_y={self.max_y}, crs='{self.crs}')"
        )

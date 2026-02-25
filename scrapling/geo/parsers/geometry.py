"""Parse and construct geometric features from scraped data."""

from __future__ import annotations

from typing import Any

from shapely.geometry import (
    LineString,
    Point,
    Polygon,
    shape,
)
from shapely.geometry.base import BaseGeometry
from shapely import wkt as shapely_wkt, wkb as shapely_wkb
from shapely.validation import make_valid

from scrapling.geo.models import GeoPoint


class GeometryParser:
    """Parse, construct, and analyse Shapely geometries."""

    # ── Parsing ─────────────────────────────────────────────────────────

    @staticmethod
    def parse_wkt(wkt: str) -> BaseGeometry:
        """Parse a Well-Known Text string."""
        return shapely_wkt.loads(wkt)

    @staticmethod
    def parse_wkb(wkb: bytes) -> BaseGeometry:
        """Parse a Well-Known Binary blob."""
        return shapely_wkb.loads(wkb)

    @staticmethod
    def parse_geojson_geometry(geojson: dict) -> BaseGeometry:
        """Parse a GeoJSON geometry dict into a Shapely object."""
        return shape(geojson)

    # ── Construction ────────────────────────────────────────────────────

    @staticmethod
    def points_to_line(points: list[GeoPoint]) -> LineString:
        """Create a LineString from a list of GeoPoints."""
        return LineString([(p.x, p.y) for p in points])

    @staticmethod
    def points_to_polygon(points: list[GeoPoint]) -> Polygon:
        """Create a Polygon from a list of GeoPoints.

        The ring is automatically closed if the first and last point differ.
        """
        coords = [(p.x, p.y) for p in points]
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])
        return Polygon(coords)

    # ── Measurement ─────────────────────────────────────────────────────

    @staticmethod
    def calculate_area(geometry: BaseGeometry, crs: str = "EPSG:4326") -> float:
        """Calculate area in square metres.

        If the geometry is in a geographic CRS the area is computed via a
        geodesic approach using ``pyproj``.
        """
        from pyproj import CRS, Geod

        crs_obj = CRS.from_user_input(crs)
        if crs_obj.is_geographic:
            geod = crs_obj.get_geod() or Geod(ellps="WGS84")
            area, _ = geod.geometry_area_perimeter(geometry)
            return abs(area)
        return geometry.area

    @staticmethod
    def calculate_distance(
        p1: GeoPoint | tuple,
        p2: GeoPoint | tuple,
        method: str = "geodesic",
    ) -> float:
        """Calculate distance between two points in metres.

        ``method`` can be ``"geodesic"`` (default, accurate) or ``"euclidean"``.
        """
        if isinstance(p1, GeoPoint):
            c1 = (p1.y, p1.x)  # (lat, lon)
        else:
            c1 = (p1[1], p1[0])

        if isinstance(p2, GeoPoint):
            c2 = (p2.y, p2.x)
        else:
            c2 = (p2[1], p2[0])

        if method == "geodesic":
            from pyproj import Geod

            geod = Geod(ellps="WGS84")
            _, _, dist = geod.inv(c1[1], c1[0], c2[1], c2[0])
            return abs(dist)
        else:
            import math

            dx = c1[1] - c2[1]
            dy = c1[0] - c2[0]
            return math.sqrt(dx * dx + dy * dy)

    # ── Manipulation ────────────────────────────────────────────────────

    @staticmethod
    def simplify(geometry: BaseGeometry, tolerance: float) -> BaseGeometry:
        """Simplify geometry using the Douglas-Peucker algorithm."""
        return geometry.simplify(tolerance, preserve_topology=True)

    @staticmethod
    def validate(geometry: BaseGeometry) -> tuple[bool, list[str]]:
        """Validate a geometry and return ``(is_valid, errors)``."""
        from scrapling.geo.validators.geometry import GeometryValidator

        return GeometryValidator().validate(geometry)

    @staticmethod
    def buffer(
        geometry: BaseGeometry,
        distance_m: float,
        crs: str = "EPSG:4326",
    ) -> BaseGeometry:
        """Buffer a geometry by *distance_m* metres.

        For geographic CRS the geometry is temporarily projected to an
        appropriate UTM zone.
        """
        from pyproj import CRS as ProjCRS

        crs_obj = ProjCRS.from_user_input(crs)
        if crs_obj.is_geographic:
            from scrapling.geo.crs.manager import CRSManager
            from shapely.ops import transform as shapely_transform

            mgr = CRSManager()
            centroid = geometry.centroid
            utm_code = mgr.get_utm_zone(centroid.x, centroid.y)
            to_utm = mgr.get_transformer(crs, utm_code)
            to_geo = mgr.get_transformer(utm_code, crs)
            projected = shapely_transform(to_utm, geometry)
            buffered = projected.buffer(distance_m)
            return shapely_transform(to_geo, buffered)
        return geometry.buffer(distance_m)

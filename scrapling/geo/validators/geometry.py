"""Geometry validation and topology repair utilities."""

from __future__ import annotations

from shapely.geometry.base import BaseGeometry
from shapely.validation import explain_validity, make_valid
from shapely import is_valid


class GeometryValidator:
    """Validate and repair Shapely geometries."""

    def validate(self, geometry: BaseGeometry) -> tuple[bool, list[str]]:
        """Validate a geometry and return (is_valid, list_of_issues)."""
        errors: list[str] = []

        if geometry.is_empty:
            errors.append("Geometry is empty")
            return (False, errors)

        if not is_valid(geometry):
            reason = explain_validity(geometry)
            errors.append(f"Invalid geometry: {reason}")

        if geometry.geom_type == "Polygon":
            if not self.check_winding_order(geometry):
                errors.append("Exterior ring is not counter-clockwise (RFC 7946)")
            if self.check_self_intersection(geometry):
                errors.append("Geometry has self-intersections")

        return (len(errors) == 0, errors)

    def fix_topology(self, geometry: BaseGeometry) -> BaseGeometry:
        """Attempt to repair topology issues and return a valid geometry."""
        if is_valid(geometry):
            return geometry
        return make_valid(geometry)

    def check_self_intersection(self, geometry: BaseGeometry) -> bool:
        """Return ``True`` if the geometry has self-intersections."""
        if not is_valid(geometry):
            explanation = explain_validity(geometry)
            return "Self-intersection" in explanation
        return False

    def check_winding_order(self, polygon) -> bool:
        """Return ``True`` if the polygon exterior ring is counter-clockwise.

        The GeoJSON spec (RFC 7946) requires CCW exterior rings.
        """
        if polygon.geom_type != "Polygon":
            return True  # Not applicable
        ring = polygon.exterior
        if ring is None:
            return True
        return ring.is_ccw

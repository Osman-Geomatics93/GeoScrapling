"""Bounding box operations."""

from __future__ import annotations

from scrapling.geo.models import BoundingBox, GeoPoint


def bbox_from_points(points: list[GeoPoint], crs: str = "EPSG:4326") -> BoundingBox:
    """Compute the bounding box that encloses all given points."""
    if not points:
        raise ValueError("Cannot compute bbox from an empty list")

    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return BoundingBox(
        min_x=min(xs),
        min_y=min(ys),
        max_x=max(xs),
        max_y=max(ys),
        crs=crs,
    )


def bbox_union(a: BoundingBox, b: BoundingBox) -> BoundingBox:
    """Return the smallest BoundingBox that contains both *a* and *b*."""
    if a.crs != b.crs:
        b = b.transform(a.crs)
    return BoundingBox(
        min_x=min(a.min_x, b.min_x),
        min_y=min(a.min_y, b.min_y),
        max_x=max(a.max_x, b.max_x),
        max_y=max(a.max_y, b.max_y),
        crs=a.crs,
    )


def bbox_intersection(a: BoundingBox, b: BoundingBox) -> BoundingBox | None:
    """Return the intersection of two bounding boxes, or ``None`` if disjoint."""
    if a.crs != b.crs:
        b = b.transform(a.crs)
    if not a.intersects(b):
        return None
    return BoundingBox(
        min_x=max(a.min_x, b.min_x),
        min_y=max(a.min_y, b.min_y),
        max_x=min(a.max_x, b.max_x),
        max_y=min(a.max_y, b.max_y),
        crs=a.crs,
    )

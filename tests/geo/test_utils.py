"""Tests for scrapling.geo.utils — bbox, units, projections."""

import math

import pytest

from scrapling.geo.models import GeoPoint, BoundingBox
from scrapling.geo.utils.bbox import bbox_from_points, bbox_union, bbox_intersection
from scrapling.geo.utils.units import (
    meters_to_feet,
    feet_to_meters,
    degrees_to_meters,
    meters_to_degrees,
    sq_meters_to_acres,
    sq_meters_to_hectares,
)
from scrapling.geo.utils.projections import (
    auto_utm_epsg,
    lon_lat_to_web_mercator,
    web_mercator_to_lon_lat,
    is_geographic,
    is_projected,
)


# ═══════════════════════════════════════════════════════════════════════════
# BBox operations
# ═══════════════════════════════════════════════════════════════════════════


class TestBBoxFromPoints:
    """Test bbox_from_points helper."""

    def test_basic(self):
        """Test computing a bbox from a list of points."""
        points = [
            GeoPoint(x=-74.006, y=40.7128),
            GeoPoint(x=-0.1276, y=51.5074),
            GeoPoint(x=2.3522, y=48.8566),
        ]
        bb = bbox_from_points(points)
        assert bb.min_x == pytest.approx(-74.006)
        assert bb.max_x == pytest.approx(2.3522)
        assert bb.min_y == pytest.approx(40.7128)
        assert bb.max_y == pytest.approx(51.5074)

    def test_single_point(self):
        """Test bbox from a single point is a zero-area box."""
        bb = bbox_from_points([GeoPoint(x=10, y=20)])
        assert bb.min_x == bb.max_x == 10
        assert bb.min_y == bb.max_y == 20

    def test_empty_raises(self):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            bbox_from_points([])


class TestBBoxUnion:
    """Test bbox_union helper."""

    def test_union(self):
        """Test union of two overlapping boxes."""
        a = BoundingBox(min_x=0, min_y=0, max_x=2, max_y=2)
        b = BoundingBox(min_x=1, min_y=1, max_x=3, max_y=3)
        u = bbox_union(a, b)
        assert u.min_x == 0
        assert u.min_y == 0
        assert u.max_x == 3
        assert u.max_y == 3

    def test_union_disjoint(self):
        """Test union of two disjoint boxes."""
        a = BoundingBox(min_x=0, min_y=0, max_x=1, max_y=1)
        b = BoundingBox(min_x=5, min_y=5, max_x=6, max_y=6)
        u = bbox_union(a, b)
        assert u.min_x == 0
        assert u.max_x == 6


class TestBBoxIntersection:
    """Test bbox_intersection helper."""

    def test_intersection_overlapping(self):
        """Test intersection of overlapping boxes."""
        a = BoundingBox(min_x=0, min_y=0, max_x=2, max_y=2)
        b = BoundingBox(min_x=1, min_y=1, max_x=3, max_y=3)
        inter = bbox_intersection(a, b)
        assert inter is not None
        assert inter.min_x == 1
        assert inter.min_y == 1
        assert inter.max_x == 2
        assert inter.max_y == 2

    def test_intersection_disjoint(self):
        """Test intersection of disjoint boxes returns None."""
        a = BoundingBox(min_x=0, min_y=0, max_x=1, max_y=1)
        b = BoundingBox(min_x=5, min_y=5, max_x=6, max_y=6)
        assert bbox_intersection(a, b) is None


# ═══════════════════════════════════════════════════════════════════════════
# Unit conversions
# ═══════════════════════════════════════════════════════════════════════════


class TestLengthConversions:
    """Test length unit conversions."""

    def test_meters_to_feet(self):
        """Test metres to feet conversion."""
        assert meters_to_feet(1.0) == pytest.approx(3.28084, rel=0.001)

    def test_feet_to_meters(self):
        """Test feet to metres conversion."""
        assert feet_to_meters(1.0) == pytest.approx(0.3048)

    def test_roundtrip_feet_meters(self):
        """Test feet→metres→feet roundtrip."""
        original = 100.0
        assert meters_to_feet(feet_to_meters(original)) == pytest.approx(original)

    def test_degrees_to_meters_equator(self):
        """Test degree-to-metre conversion at the equator."""
        # 1 degree ≈ 111,320 m at the equator
        assert degrees_to_meters(1.0, latitude=0) == pytest.approx(111_320, rel=0.01)

    def test_degrees_to_meters_at_latitude(self):
        """Test degree-to-metre conversion at a higher latitude."""
        m = degrees_to_meters(1.0, latitude=60)
        # At 60° latitude, 1 degree ≈ 55,660 m (cos(60°) = 0.5)
        assert m == pytest.approx(55_660, rel=0.01)

    def test_meters_to_degrees_equator(self):
        """Test metre-to-degree conversion at the equator."""
        assert meters_to_degrees(111_320, latitude=0) == pytest.approx(1.0, rel=0.01)

    def test_roundtrip_degrees_meters(self):
        """Test degree→metre→degree roundtrip."""
        original = 0.5
        lat = 45.0
        result = meters_to_degrees(degrees_to_meters(original, lat), lat)
        assert result == pytest.approx(original, rel=0.001)


class TestAreaConversions:
    """Test area unit conversions."""

    def test_sq_meters_to_acres(self):
        """Test square metres to acres."""
        assert sq_meters_to_acres(4046.8564224) == pytest.approx(1.0)

    def test_sq_meters_to_hectares(self):
        """Test square metres to hectares."""
        assert sq_meters_to_hectares(10_000) == pytest.approx(1.0)


# ═══════════════════════════════════════════════════════════════════════════
# Projection helpers
# ═══════════════════════════════════════════════════════════════════════════


class TestProjectionHelpers:
    """Test common projection helper functions."""

    @pytest.mark.parametrize("lon,lat,expected", [
        (-74.006, 40.7128, "EPSG:32618"),
        (0, 51.5, "EPSG:32631"),
        (151.2, -33.9, "EPSG:32756"),
        (-180, 0, "EPSG:32601"),
    ])
    def test_auto_utm_epsg(self, lon, lat, expected):
        """Test auto UTM EPSG detection."""
        assert auto_utm_epsg(lon, lat) == expected

    def test_web_mercator_roundtrip(self):
        """Test lon/lat → Web Mercator → lon/lat roundtrip."""
        lon, lat = -74.006, 40.7128
        x, y = lon_lat_to_web_mercator(lon, lat)
        lon2, lat2 = web_mercator_to_lon_lat(x, y)
        assert lon2 == pytest.approx(lon, abs=0.001)
        assert lat2 == pytest.approx(lat, abs=0.001)

    def test_web_mercator_origin(self):
        """Test (0, 0) maps to (0, 0) in Web Mercator."""
        x, y = lon_lat_to_web_mercator(0, 0)
        assert x == pytest.approx(0, abs=1)
        assert y == pytest.approx(0, abs=1)

    def test_is_geographic(self):
        """Test geographic CRS detection."""
        assert is_geographic("EPSG:4326") is True
        assert is_geographic("EPSG:32618") is False

    def test_is_projected(self):
        """Test projected CRS detection."""
        assert is_projected("EPSG:32618") is True
        assert is_projected("EPSG:4326") is False

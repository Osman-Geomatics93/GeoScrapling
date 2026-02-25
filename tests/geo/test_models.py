"""Tests for scrapling.geo.models — GeoPoint, GeoFeature, BoundingBox."""

import pytest
from shapely.geometry import Point, Polygon, box, mapping

from scrapling.geo.models import GeoPoint, GeoFeature, BoundingBox, CoordinateQuality


class TestCoordinateQuality:
    """Test CoordinateQuality dataclass."""

    def test_default_values(self):
        """Test default field values."""
        q = CoordinateQuality()
        assert q.precision == 6
        assert q.accuracy_m == 0.0
        assert q.source == "unknown"
        assert q.confidence == 1.0
        assert q.crs == "EPSG:4326"

    def test_to_dict(self, sample_quality):
        """Test serialisation to dictionary."""
        d = sample_quality.to_dict()
        assert d["precision"] == 6
        assert d["accuracy_m"] == 1.5
        assert d["source"] == "gps"
        assert d["method"] == "rtk"
        assert d["confidence"] == 0.95

    def test_meets_tolerance_pass(self, sample_quality):
        """Test meets_tolerance when accuracy is within tolerance."""
        assert sample_quality.meets_tolerance(2.0) is True

    def test_meets_tolerance_fail(self, sample_quality):
        """Test meets_tolerance when accuracy exceeds tolerance."""
        assert sample_quality.meets_tolerance(1.0) is False

    def test_meets_tolerance_exact(self, sample_quality):
        """Test meets_tolerance when accuracy equals tolerance."""
        assert sample_quality.meets_tolerance(1.5) is True


class TestGeoPoint:
    """Test GeoPoint dataclass."""

    def test_create_2d(self):
        """Test creating a 2D point."""
        p = GeoPoint(x=-74.006, y=40.7128)
        assert p.x == -74.006
        assert p.y == 40.7128
        assert p.z is None
        assert p.crs == "EPSG:4326"

    def test_create_3d(self, point_with_elevation):
        """Test creating a 3D point with elevation."""
        assert point_with_elevation.z == 34.0

    def test_to_shapely_2d(self, wgs84_point):
        """Test converting to a Shapely Point (2D)."""
        shapely_pt = wgs84_point.to_shapely()
        assert isinstance(shapely_pt, Point)
        assert shapely_pt.x == pytest.approx(-74.006)
        assert shapely_pt.y == pytest.approx(40.7128)

    def test_to_shapely_3d(self, point_with_elevation):
        """Test converting to a Shapely Point (3D)."""
        shapely_pt = point_with_elevation.to_shapely()
        assert shapely_pt.has_z
        assert shapely_pt.z == pytest.approx(34.0)

    def test_to_tuple_2d(self, wgs84_point):
        """Test tuple conversion for 2D point."""
        t = wgs84_point.to_tuple()
        assert len(t) == 2
        assert t == (-74.006, 40.7128)

    def test_to_tuple_3d(self, point_with_elevation):
        """Test tuple conversion for 3D point."""
        t = point_with_elevation.to_tuple()
        assert len(t) == 3
        assert t[2] == 34.0

    def test_to_wgs84_already_wgs84(self, wgs84_point):
        """Test that to_wgs84 is a no-op for WGS84 points."""
        result = wgs84_point.to_wgs84()
        assert result is wgs84_point

    def test_to_wgs84_from_utm(self, utm_point):
        """Test transforming a UTM point to WGS84."""
        wgs = utm_point.to_wgs84()
        assert wgs.crs == "EPSG:4326"
        assert wgs.y == pytest.approx(40.7128, abs=0.01)
        assert wgs.x == pytest.approx(-74.006, abs=0.01)

    def test_repr(self, wgs84_point):
        """Test string representation."""
        r = repr(wgs84_point)
        assert "GeoPoint" in r
        assert "-74.006" in r
        assert "EPSG:4326" in r

    def test_repr_with_z(self, point_with_elevation):
        """Test repr includes z when present."""
        r = repr(point_with_elevation)
        assert "z=34.0" in r


class TestGeoFeature:
    """Test GeoFeature dataclass."""

    def test_create(self, sample_feature):
        """Test creating a feature with geometry and properties."""
        assert sample_feature.crs == "EPSG:4326"
        assert sample_feature.id == "feat-001"
        assert sample_feature.properties["name"] == "Test Polygon"

    def test_to_geojson(self, sample_feature):
        """Test GeoJSON serialisation."""
        gj = sample_feature.to_geojson()
        assert gj["type"] == "Feature"
        assert gj["geometry"]["type"] == "Polygon"
        assert gj["id"] == "feat-001"
        assert gj["properties"]["name"] == "Test Polygon"
        assert gj["properties"]["area_code"] == 42

    def test_to_geojson_no_id(self, sample_polygon):
        """Test GeoJSON without an explicit feature ID."""
        feat = GeoFeature(geometry=sample_polygon, properties={})
        gj = feat.to_geojson()
        assert "id" not in gj

    def test_transform_same_crs(self, sample_feature):
        """Test transform is a no-op when CRS already matches."""
        result = sample_feature.transform("EPSG:4326")
        assert result is sample_feature

    def test_transform_to_different_crs(self):
        """Test transforming a feature to a different CRS."""
        feat = GeoFeature(
            geometry=Point(-74.006, 40.7128),
            properties={"name": "NYC"},
            crs="EPSG:4326",
        )
        transformed = feat.transform("EPSG:3857")
        assert transformed.crs == "EPSG:3857"
        # Web Mercator x should be around -8.2M
        assert transformed.geometry.centroid.x == pytest.approx(-8238310, rel=0.01)

    def test_repr(self, sample_feature):
        """Test string representation."""
        r = repr(sample_feature)
        assert "Polygon" in r
        assert "feat-001" in r


class TestBoundingBox:
    """Test BoundingBox dataclass."""

    def test_create(self, nyc_bbox):
        """Test creation with explicit coordinates."""
        assert nyc_bbox.min_x == -74.3
        assert nyc_bbox.max_y == 40.9
        assert nyc_bbox.crs == "EPSG:4326"

    def test_to_polygon(self, nyc_bbox):
        """Test conversion to a Shapely Polygon."""
        poly = nyc_bbox.to_polygon()
        assert isinstance(poly, Polygon)
        assert poly.is_valid
        bounds = poly.bounds
        assert bounds[0] == pytest.approx(-74.3)
        assert bounds[2] == pytest.approx(-73.7)

    def test_contains_inside(self, nyc_bbox, wgs84_point):
        """Test contains returns True for a point inside the box."""
        assert nyc_bbox.contains(wgs84_point) is True

    def test_contains_outside(self, nyc_bbox, london_point):
        """Test contains returns False for a point outside the box."""
        assert nyc_bbox.contains(london_point) is False

    def test_intersects_overlapping(self, nyc_bbox):
        """Test intersects returns True for overlapping boxes."""
        other = BoundingBox(min_x=-74.0, min_y=40.6, max_x=-73.5, max_y=41.0)
        assert nyc_bbox.intersects(other) is True

    def test_intersects_disjoint(self, nyc_bbox):
        """Test intersects returns False for disjoint boxes."""
        other = BoundingBox(min_x=0, min_y=0, max_x=1, max_y=1)
        assert nyc_bbox.intersects(other) is False

    def test_intersects_touching(self):
        """Test intersects returns True for boxes sharing an edge."""
        a = BoundingBox(min_x=0, min_y=0, max_x=1, max_y=1)
        b = BoundingBox(min_x=1, min_y=0, max_x=2, max_y=1)
        assert a.intersects(b) is True

    def test_transform(self, nyc_bbox):
        """Test transforming a bbox to a different CRS."""
        utm = nyc_bbox.transform("EPSG:32618")
        assert utm.crs == "EPSG:32618"
        # UTM eastings should be in the hundreds-of-thousands range
        assert utm.min_x > 100_000
        assert utm.max_x < 900_000

    def test_transform_same_crs(self, nyc_bbox):
        """Test transform is a no-op when CRS matches."""
        result = nyc_bbox.transform("EPSG:4326")
        assert result is nyc_bbox

    def test_to_tuple(self, nyc_bbox):
        """Test tuple conversion."""
        t = nyc_bbox.to_tuple()
        assert t == (-74.3, 40.5, -73.7, 40.9)

    def test_repr(self, nyc_bbox):
        """Test string representation."""
        r = repr(nyc_bbox)
        assert "BoundingBox" in r
        assert "-74.3" in r

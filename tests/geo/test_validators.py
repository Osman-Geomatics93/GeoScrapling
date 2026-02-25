"""Tests for scrapling.geo.validators — CoordinateValidator, GeometryValidator."""

import pytest
from shapely.geometry import Point, Polygon, LineString
from shapely.validation import make_valid

from scrapling.geo.validators.coordinates import CoordinateValidator
from scrapling.geo.validators.geometry import GeometryValidator


# ── CoordinateValidator ─────────────────────────────────────────────────────


class TestCoordinateValidatorLatLon:
    """Test WGS84 latitude/longitude validation."""

    @pytest.fixture
    def validator(self):
        return CoordinateValidator()

    def test_valid_coords(self, validator):
        """Test valid lat/lon pair."""
        valid, errors = validator.validate_lat_lon(40.7128, -74.006)
        assert valid is True
        assert errors == []

    def test_zero_coords(self, validator):
        """Test zero coordinates (null island)."""
        valid, errors = validator.validate_lat_lon(0, 0)
        assert valid is True

    def test_extreme_valid_coords(self, validator):
        """Test boundary values."""
        valid, errors = validator.validate_lat_lon(90, 180)
        assert valid is True
        valid, errors = validator.validate_lat_lon(-90, -180)
        assert valid is True

    def test_lat_out_of_range(self, validator):
        """Test latitude out of range."""
        valid, errors = validator.validate_lat_lon(91, 0)
        assert valid is False
        assert len(errors) == 1
        assert "Latitude" in errors[0]

    def test_lon_out_of_range(self, validator):
        """Test longitude out of range."""
        valid, errors = validator.validate_lat_lon(0, 181)
        assert valid is False
        assert len(errors) == 1
        assert "Longitude" in errors[0]

    def test_both_out_of_range(self, validator):
        """Test both lat and lon out of range."""
        valid, errors = validator.validate_lat_lon(-91, 200)
        assert valid is False
        assert len(errors) == 2


class TestCoordinateValidatorUTM:
    """Test UTM coordinate validation."""

    @pytest.fixture
    def validator(self):
        return CoordinateValidator()

    def test_valid_utm(self, validator):
        """Test valid UTM coordinates."""
        valid, errors = validator.validate_utm(583960, 4507523, 18)
        assert valid is True
        assert errors == []

    def test_invalid_zone(self, validator):
        """Test UTM zone out of range."""
        valid, errors = validator.validate_utm(500000, 5000000, 61)
        assert valid is False
        assert any("zone" in e.lower() for e in errors)

    def test_invalid_easting(self, validator):
        """Test easting out of typical range."""
        valid, errors = validator.validate_utm(50000, 5000000, 18)
        assert valid is False
        assert any("Easting" in e for e in errors)

    def test_invalid_northing(self, validator):
        """Test northing out of range."""
        valid, errors = validator.validate_utm(500000, -100, 18)
        assert valid is False
        assert any("Northing" in e for e in errors)


class TestCoordinateValidatorPrecision:
    """Test coordinate precision validation."""

    @pytest.fixture
    def validator(self):
        return CoordinateValidator()

    @pytest.mark.parametrize("coord,min_dec,expected", [
        (40.7128, 4, True),
        (40.7128, 5, False),
        (40.0, 0, True),
        (40.0, 1, False),
        (40.71280000, 4, True),
    ])
    def test_validate_precision(self, validator, coord, min_dec, expected):
        """Test precision validation with various inputs."""
        assert validator.validate_precision(coord, min_dec) is expected


class TestCoordinateValidatorCountry:
    """Test country bounding box validation."""

    @pytest.fixture
    def validator(self):
        return CoordinateValidator()

    def test_point_in_us(self, validator):
        """Test point inside US bounding box."""
        assert validator.check_in_country(40.7128, -74.006, "US") is True

    def test_point_outside_us(self, validator):
        """Test point outside US bounding box."""
        assert validator.check_in_country(51.5, -0.1, "US") is False

    def test_point_in_gb(self, validator):
        """Test point inside UK bounding box."""
        assert validator.check_in_country(51.5, -0.1, "GB") is True

    def test_unknown_country(self, validator):
        """Test unknown country code returns True (cannot reject)."""
        assert validator.check_in_country(0, 0, "ZZ") is True


# ── GeometryValidator ───────────────────────────────────────────────────────


class TestGeometryValidatorValidate:
    """Test geometry validation."""

    @pytest.fixture
    def validator(self):
        return GeometryValidator()

    def test_valid_polygon(self, validator, sample_polygon):
        """Test a valid simple polygon."""
        valid, errors = validator.validate(sample_polygon)
        assert valid is True
        assert errors == []

    def test_valid_linestring(self, validator, sample_linestring):
        """Test a valid LineString."""
        valid, errors = validator.validate(sample_linestring)
        assert valid is True

    def test_valid_point(self, validator, sample_point):
        """Test a valid Point."""
        valid, errors = validator.validate(sample_point)
        assert valid is True

    def test_empty_geometry(self, validator):
        """Test empty geometry is invalid."""
        empty = Point()
        valid, errors = validator.validate(empty)
        assert valid is False
        assert any("empty" in e.lower() for e in errors)

    def test_self_intersecting_polygon(self, validator, self_intersecting_polygon):
        """Test self-intersecting polygon is detected."""
        valid, errors = validator.validate(self_intersecting_polygon)
        assert valid is False
        assert len(errors) > 0


class TestGeometryValidatorFix:
    """Test geometry topology repair."""

    @pytest.fixture
    def validator(self):
        return GeometryValidator()

    def test_fix_already_valid(self, validator, sample_polygon):
        """Test fixing an already-valid geometry returns it unchanged."""
        fixed = validator.fix_topology(sample_polygon)
        assert fixed.equals(sample_polygon)

    def test_fix_self_intersection(self, validator, self_intersecting_polygon):
        """Test fixing a self-intersecting polygon."""
        fixed = validator.fix_topology(self_intersecting_polygon)
        assert fixed.is_valid


class TestGeometryValidatorChecks:
    """Test individual geometry checks."""

    @pytest.fixture
    def validator(self):
        return GeometryValidator()

    def test_check_self_intersection_clean(self, validator, sample_polygon):
        """Test no self-intersection on a clean polygon."""
        assert validator.check_self_intersection(sample_polygon) is False

    def test_check_self_intersection_bowtie(self, validator, self_intersecting_polygon):
        """Test self-intersection on a bowtie polygon."""
        assert validator.check_self_intersection(self_intersecting_polygon) is True

    def test_check_winding_order_ccw(self, validator):
        """Test CCW exterior ring passes."""
        # Shapely creates CCW polygons by default
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        assert validator.check_winding_order(poly) is True

    def test_check_winding_order_non_polygon(self, validator, sample_linestring):
        """Test winding order check returns True for non-polygons."""
        assert validator.check_winding_order(sample_linestring) is True

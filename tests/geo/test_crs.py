"""Tests for scrapling.geo.crs — CRSManager, CRSRegistry, quality helpers."""

import pytest
from pyproj import CRS

from scrapling.geo.crs.manager import CRSManager
from scrapling.geo.crs.registry import CRSRegistry
from scrapling.geo.crs.quality import estimate_precision, precision_to_accuracy


# ── CRSManager ──────────────────────────────────────────────────────────────


class TestCRSManagerInit:
    """Test CRSManager initialisation."""

    def test_default_crs(self):
        """Test default CRS is WGS84."""
        mgr = CRSManager()
        assert mgr.default_crs == CRS.from_epsg(4326)

    def test_custom_default_crs(self):
        """Test initialisation with a custom default CRS."""
        mgr = CRSManager(default_crs="EPSG:3857")
        assert mgr.default_crs == CRS.from_epsg(3857)


class TestCRSManagerTransform:
    """Test coordinate transformation methods."""

    @pytest.fixture
    def mgr(self):
        return CRSManager()

    def test_transform_identity(self, mgr):
        """Test transforming between the same CRS returns original coords."""
        coords = [(-74.006, 40.7128)]
        result = mgr.transform(coords, "EPSG:4326", "EPSG:4326")
        assert result[0][0] == pytest.approx(-74.006, abs=1e-6)
        assert result[0][1] == pytest.approx(40.7128, abs=1e-6)

    def test_transform_wgs84_to_utm(self, mgr):
        """Test WGS84 to UTM zone 18N transformation."""
        coords = [(-74.006, 40.7128)]
        result = mgr.transform(coords, "EPSG:4326", "EPSG:32618")
        # UTM easting should be ~584000
        assert result[0][0] == pytest.approx(583960, abs=200)
        # UTM northing should be ~4507000-4508000 range
        assert result[0][1] == pytest.approx(4507400, abs=500)

    def test_transform_multiple_points(self, mgr):
        """Test transforming multiple points at once."""
        coords = [(-74.006, 40.7128), (-0.1276, 51.5074)]
        result = mgr.transform(coords, "EPSG:4326", "EPSG:3857")
        assert len(result) == 2
        # NYC in Web Mercator
        assert result[0][0] == pytest.approx(-8238310, rel=0.01)
        # London in Web Mercator
        assert result[1][0] == pytest.approx(-14203, rel=0.1)

    def test_to_wgs84(self, mgr):
        """Test shortcut to WGS84."""
        utm_coords = [(583960.0, 4507523.0)]
        result = mgr.to_wgs84(utm_coords, "EPSG:32618")
        assert result[0][1] == pytest.approx(40.7128, abs=0.01)
        assert result[0][0] == pytest.approx(-74.006, abs=0.01)

    def test_to_utm_auto_detect(self, mgr):
        """Test auto-detection of UTM zone."""
        coords = [(-74.006, 40.7128)]
        result, utm_code = mgr.to_utm(coords, "EPSG:4326")
        assert utm_code == "EPSG:32618"
        assert result[0][0] == pytest.approx(583960, abs=100)

    def test_to_utm_southern_hemisphere(self, mgr):
        """Test UTM zone detection for southern hemisphere."""
        coords = [(151.2093, -33.8688)]  # Sydney
        result, utm_code = mgr.to_utm(coords, "EPSG:4326")
        assert utm_code == "EPSG:32756"

    def test_to_local_grid(self, mgr):
        """Test transform to a national grid using alias."""
        coords = [(-0.1276, 51.5074)]  # London
        result = mgr.to_local_grid(coords, "OSGB36", from_crs="EPSG:4326")
        # OSGB eastings should be ~530000
        assert result[0][0] == pytest.approx(530000, abs=5000)


class TestCRSManagerDatum:
    """Test datum transformation and geoid methods."""

    @pytest.fixture
    def mgr(self):
        return CRSManager()

    def test_datum_transform(self, mgr):
        """Test datum transformation delegates to transform."""
        coords = [(-74.006, 40.7128)]
        result = mgr.datum_transform(coords, "EPSG:4326", "EPSG:4269")
        # NAD83 and WGS84 are nearly identical
        assert result[0][0] == pytest.approx(-74.006, abs=0.001)

    def test_get_geoid_height(self, mgr):
        """Test geoid height returns a numeric value."""
        n = mgr.get_geoid_height(40.7128, -74.006)
        assert isinstance(n, float)

    def test_ellipsoidal_to_orthometric(self, mgr):
        """Test ellipsoidal-to-orthometric height conversion."""
        ortho = mgr.ellipsoidal_to_orthometric(40.7128, -74.006, 50.0)
        assert isinstance(ortho, float)
        # The result should be close to 50 minus the geoid undulation
        assert abs(ortho) < 100


class TestCRSManagerUtilities:
    """Test CRS utility methods."""

    @pytest.fixture
    def mgr(self):
        return CRSManager()

    def test_detect_crs_epsg(self, mgr):
        """Test detecting CRS from EPSG code."""
        crs = mgr.detect_crs("EPSG:4326")
        assert crs == CRS.from_epsg(4326)

    def test_detect_crs_proj_string(self, mgr):
        """Test detecting CRS from a PROJ string."""
        crs = mgr.detect_crs("+proj=longlat +datum=WGS84")
        assert crs.is_geographic

    def test_get_utm_zone_northern(self, mgr):
        """Test UTM zone for northern hemisphere."""
        assert mgr.get_utm_zone(-74.006, 40.7128) == "EPSG:32618"

    def test_get_utm_zone_southern(self, mgr):
        """Test UTM zone for southern hemisphere."""
        assert mgr.get_utm_zone(151.2093, -33.8688) == "EPSG:32756"

    @pytest.mark.parametrize("lon,expected_zone", [
        (-180, 1), (-174, 2), (-168, 3), (0, 31), (6, 32), (174, 60),
    ])
    def test_get_utm_zone_numbers(self, mgr, lon, expected_zone):
        """Test UTM zone number calculation for various longitudes."""
        result = mgr.get_utm_zone(lon, 45.0)
        assert result == f"EPSG:326{expected_zone:02d}"

    def test_crs_info(self, mgr):
        """Test CRS metadata retrieval."""
        info = mgr.crs_info("EPSG:4326")
        assert info["name"] == "WGS 84"
        assert info["is_geographic"] is True
        assert info["is_projected"] is False
        assert info["datum"] is not None

    def test_crs_info_projected(self, mgr):
        """Test CRS info for a projected CRS."""
        info = mgr.crs_info("EPSG:32618")
        assert info["is_projected"] is True
        assert info["is_geographic"] is False

    def test_get_transformer_callable(self, mgr):
        """Test get_transformer returns a callable for shapely.ops.transform."""
        fn = mgr.get_transformer("EPSG:4326", "EPSG:3857")
        assert callable(fn)
        x, y = fn(-74.006, 40.7128)
        assert x == pytest.approx(-8238310, rel=0.01)


# ── CRSRegistry ─────────────────────────────────────────────────────────────


class TestCRSRegistry:
    """Test CRSRegistry alias resolution and lookup."""

    @pytest.fixture
    def registry(self):
        return CRSRegistry()

    def test_resolve_epsg(self, registry):
        """Test resolving an EPSG code returns it unchanged."""
        assert registry.resolve("EPSG:4326") == "EPSG:4326"

    def test_resolve_alias(self, registry):
        """Test resolving a well-known alias."""
        assert registry.resolve("WGS84") == "EPSG:4326"
        assert registry.resolve("OSGB36") == "EPSG:27700"
        assert registry.resolve("Web Mercator") == "EPSG:3857"

    def test_resolve_case_insensitive(self, registry):
        """Test alias resolution is case-insensitive."""
        assert registry.resolve("wgs84") == "EPSG:4326"
        assert registry.resolve("web mercator") == "EPSG:3857"

    def test_get_crs(self, registry):
        """Test getting a pyproj CRS object."""
        crs = registry.get_crs("WGS84")
        assert isinstance(crs, CRS)
        assert crs.is_geographic

    def test_register_alias(self, registry):
        """Test registering a custom alias."""
        registry.register_alias("MyGrid", "EPSG:2154")
        assert registry.resolve("MyGrid") == "EPSG:2154"

    def test_list_aliases(self, registry):
        """Test listing all aliases."""
        aliases = registry.list_aliases()
        assert "WGS84" in aliases
        assert "OSGB36" in aliases
        assert len(aliases) > 5

    def test_search(self, registry):
        """Test searching aliases by keyword."""
        results = registry.search("Swiss")
        assert len(results) >= 1
        assert any("Swiss" in r["alias"] for r in results)

    def test_search_no_results(self, registry):
        """Test searching with a keyword that has no matches."""
        results = registry.search("nonexistent_crs_xyz")
        assert len(results) == 0


# ── Quality helpers ─────────────────────────────────────────────────────────


class TestQualityHelpers:
    """Test coordinate quality utility functions."""

    @pytest.mark.parametrize("value,expected", [
        (40.7128, 4),
        (40.0, 0),
        (40.71280000, 4),
        (40.7, 1),
        (40.712800, 4),
    ])
    def test_estimate_precision(self, value, expected):
        """Test decimal precision estimation."""
        assert estimate_precision(value) == expected

    def test_precision_to_accuracy_geographic(self):
        """Test precision-to-accuracy mapping for geographic CRS."""
        acc_1 = precision_to_accuracy(1, is_geographic=True)
        acc_5 = precision_to_accuracy(5, is_geographic=True)
        # 1 decimal ≈ 11 km, 5 decimals ≈ 1.1 m
        assert acc_1 == pytest.approx(11132.0, rel=0.01)
        assert acc_5 == pytest.approx(1.1132, rel=0.01)

    def test_precision_to_accuracy_projected(self):
        """Test precision-to-accuracy mapping for projected CRS."""
        acc_0 = precision_to_accuracy(0, is_geographic=False)
        acc_3 = precision_to_accuracy(3, is_geographic=False)
        assert acc_0 == 1.0
        assert acc_3 == 0.001

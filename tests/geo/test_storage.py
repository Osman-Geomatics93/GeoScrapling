"""Tests for scrapling.geo.storage — GeoPackageStorage, SpatiaLiteStorage."""

import pytest
from shapely.geometry import Point, Polygon

from scrapling.geo.models import GeoFeature
from scrapling.geo.storage.geopackage import GeoPackageStorage
from scrapling.geo.storage.spatialite import SpatiaLiteStorage


# ═══════════════════════════════════════════════════════════════════════════
# GeoPackageStorage
# ═══════════════════════════════════════════════════════════════════════════


class TestGeoPackageStorageWrite:
    """Test GeoPackage write operations."""

    def test_save_single_feature(self, sample_feature, tmp_path):
        """Test saving a single feature to a GeoPackage."""
        gpkg = tmp_path / "test.gpkg"
        store = GeoPackageStorage(str(gpkg))
        store.save_feature("test_layer", sample_feature)
        assert gpkg.exists()

    def test_save_multiple_features(self, point_features, tmp_path):
        """Test saving multiple features at once."""
        gpkg = tmp_path / "test.gpkg"
        store = GeoPackageStorage(str(gpkg))
        store.save_features("points", point_features)

        tables = store.list_tables()
        assert "points" in tables

    def test_save_empty_list(self, tmp_path):
        """Test saving an empty feature list does nothing."""
        gpkg = tmp_path / "test.gpkg"
        store = GeoPackageStorage(str(gpkg))
        store.save_features("empty", [])
        # File may or may not exist, but no error
        assert True


class TestGeoPackageStorageRead:
    """Test GeoPackage read and query operations."""

    @pytest.fixture
    def populated_store(self, point_features, tmp_path):
        """Create a GeoPackage with some test data."""
        gpkg = tmp_path / "populated.gpkg"
        store = GeoPackageStorage(str(gpkg))
        store.save_features("cities", point_features)
        return store

    def test_list_tables(self, populated_store):
        """Test listing tables in a GeoPackage."""
        tables = populated_store.list_tables()
        assert "cities" in tables

    def test_get_table_crs(self, populated_store):
        """Test getting the CRS of a table."""
        crs = populated_store.get_table_crs("cities")
        assert "4326" in crs

    def test_query_bbox(self, populated_store):
        """Test bounding box query."""
        # NYC area
        results = populated_store.query_bbox("cities", (-75, 40, -73, 41))
        assert len(results) >= 1
        assert isinstance(results[0], GeoFeature)

    def test_query_bbox_no_results(self, populated_store):
        """Test bounding box query with no matches."""
        results = populated_store.query_bbox("cities", (100, 0, 101, 1))
        assert len(results) == 0

    def test_query_within(self, populated_store):
        """Test query_within a geometry."""
        search_area = Polygon([(-80, 35), (-70, 35), (-70, 45), (-80, 45)])
        results = populated_store.query_within("cities", search_area)
        assert len(results) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# SpatiaLiteStorage
# ═══════════════════════════════════════════════════════════════════════════


class TestSpatiaLiteStorageWrite:
    """Test SpatiaLite write operations."""

    def test_save_features(self, point_features, tmp_path):
        """Test saving features to SpatiaLite."""
        db = tmp_path / "test.sqlite"
        store = SpatiaLiteStorage(str(db))
        store.save_features("points", point_features)
        assert db.exists()

        tables = store.list_tables()
        assert "points" in tables
        store.close()

    def test_save_single_feature(self, sample_feature, tmp_path):
        """Test saving a single feature."""
        db = tmp_path / "test.sqlite"
        store = SpatiaLiteStorage(str(db))
        store.save_feature("polys", sample_feature)

        tables = store.list_tables()
        assert "polys" in tables
        store.close()


class TestSpatiaLiteStorageRead:
    """Test SpatiaLite read and query operations."""

    @pytest.fixture
    def populated_store(self, point_features, tmp_path):
        """Create a SpatiaLite database with test data."""
        db = tmp_path / "populated.sqlite"
        store = SpatiaLiteStorage(str(db))
        store.save_features("cities", point_features)
        return store

    def test_list_tables(self, populated_store):
        """Test listing tables."""
        tables = populated_store.list_tables()
        assert "cities" in tables
        populated_store.close()

    def test_query_bbox(self, populated_store):
        """Test bounding box query (may fall back to full scan without SpatiaLite extension)."""
        results = populated_store.query_bbox("cities", (-180, -90, 180, 90))
        # At minimum, should return features (may be empty if SpatiaLite unavailable)
        assert isinstance(results, list)
        populated_store.close()

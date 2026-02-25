"""Tests for scrapling.geo.exporters — GeoExporter and format-specific exporters."""

import json
import csv
import tempfile
from pathlib import Path

import pytest
import numpy as np
from shapely.geometry import Point, Polygon

from scrapling.geo.models import GeoFeature
from scrapling.geo.exporters.base import GeoExporter


class TestGeoExporterDispatch:
    """Test GeoExporter format dispatch and auto-detection."""

    @pytest.fixture
    def exporter(self):
        return GeoExporter()

    def test_auto_detect_geojson(self, exporter, point_features, tmp_path):
        """Test auto-detection of GeoJSON from file extension."""
        out = tmp_path / "test.geojson"
        result = exporter.export(point_features, str(out))
        assert result.exists()
        data = json.loads(out.read_text())
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 4

    def test_auto_detect_csv(self, exporter, point_features, tmp_path):
        """Test auto-detection of CSV from file extension."""
        out = tmp_path / "test.csv"
        result = exporter.export(point_features, str(out))
        assert result.exists()
        content = out.read_text()
        assert "lon" in content
        assert "lat" in content

    def test_explicit_format_override(self, exporter, point_features, tmp_path):
        """Test explicit format overrides extension detection."""
        out = tmp_path / "output.txt"
        result = exporter.export(point_features, str(out), format="geojson")
        assert result.exists()
        data = json.loads(out.read_text())
        assert data["type"] == "FeatureCollection"

    def test_unsupported_format(self, exporter, point_features, tmp_path):
        """Test that an unsupported format raises ValueError."""
        out = tmp_path / "test.xyz"
        with pytest.raises(ValueError, match="Unsupported export format"):
            exporter.export(point_features, str(out), format="xyz_format")


class TestGeoJSONExporter:
    """Test GeoJSON export."""

    def test_export_points(self, point_features, tmp_path):
        """Test exporting point features to GeoJSON."""
        out = tmp_path / "points.geojson"
        exporter = GeoExporter()
        exporter.to_geojson(point_features, str(out))

        data = json.loads(out.read_text())
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 4
        # Check first feature
        feat = data["features"][0]
        assert feat["type"] == "Feature"
        assert feat["geometry"]["type"] == "Point"
        assert feat["properties"]["id"] == 0

    def test_export_polygon(self, sample_feature, tmp_path):
        """Test exporting a polygon feature to GeoJSON."""
        out = tmp_path / "polygon.geojson"
        exporter = GeoExporter()
        exporter.to_geojson([sample_feature], str(out))

        data = json.loads(out.read_text())
        assert data["features"][0]["geometry"]["type"] == "Polygon"

    def test_roundtrip(self, point_features, tmp_path):
        """Test GeoJSON export/import roundtrip."""
        from scrapling.geo.parsers.coordinate import CoordinateExtractor

        out = tmp_path / "roundtrip.geojson"
        GeoExporter().to_geojson(point_features, str(out))

        extractor = CoordinateExtractor()
        reimported = extractor.extract_from_geojson(out.read_text())
        assert len(reimported) == len(point_features)


class TestCSVExporter:
    """Test CSV export."""

    def test_export_with_coords(self, point_features, tmp_path):
        """Test CSV export includes coordinate columns."""
        out = tmp_path / "test.csv"
        GeoExporter().to_csv(point_features, str(out))

        with open(str(out), newline="", encoding="utf-8") as fh:
            lines = fh.readlines()

        # First line is a CRS comment
        assert lines[0].startswith("# CRS:")
        # Second line is the header
        assert "lon" in lines[1]
        assert "lat" in lines[1]
        # Data rows
        assert len(lines) == 2 + len(point_features)  # comment + header + data

    def test_export_custom_columns(self, point_features, tmp_path):
        """Test CSV export with custom coordinate column names."""
        out = tmp_path / "custom.csv"
        GeoExporter().to_csv(point_features, str(out), coord_columns=("x", "y"))

        header = open(str(out), encoding="utf-8").readlines()[1]
        assert "x" in header
        assert "y" in header

    def test_export_empty(self, tmp_path):
        """Test CSV export with empty feature list."""
        out = tmp_path / "empty.csv"
        GeoExporter().to_csv([], str(out))
        assert out.exists()
        assert out.read_text() == ""


class TestGeoPackageExporter:
    """Test GeoPackage export."""

    def test_export_and_read(self, point_features, tmp_path):
        """Test GeoPackage export produces a valid file."""
        import geopandas as gpd

        out = tmp_path / "test.gpkg"
        GeoExporter().to_geopackage(point_features, str(out))
        assert out.exists()

        # Verify with geopandas
        gdf = gpd.read_file(str(out))
        assert len(gdf) == 4
        assert gdf.crs is not None

    def test_export_empty_raises(self, tmp_path):
        """Test GeoPackage export with empty list raises ValueError."""
        out = tmp_path / "empty.gpkg"
        with pytest.raises(ValueError, match="No features"):
            GeoExporter().to_geopackage([], str(out))


class TestGeoTIFFExporter:
    """Test GeoTIFF raster export."""

    @staticmethod
    def _rasterio_crs_works():
        """Check if rasterio CRS is functional (can fail with conflicting PROJ installs)."""
        try:
            from rasterio.crs import CRS as RioCRS
            RioCRS.from_user_input("EPSG:4326")
            return True
        except Exception:
            return False

    @pytest.mark.skipif(
        not _rasterio_crs_works.__func__(),
        reason="rasterio CRS not functional (conflicting PROJ database)",
    )
    def test_export_2d_array(self, tmp_path):
        """Test exporting a 2D numpy array as GeoTIFF."""
        from rasterio.transform import from_bounds

        data = np.random.rand(100, 100).astype(np.float32)
        transform = from_bounds(0, 0, 1, 1, 100, 100)
        out = tmp_path / "test.tif"

        exporter = GeoExporter()
        exporter.to_geotiff(data, str(out), crs="EPSG:4326", transform=transform)
        assert out.exists()

        import rasterio
        with rasterio.open(str(out)) as src:
            assert src.count == 1
            assert src.width == 100
            assert src.height == 100

    @pytest.mark.skipif(
        not _rasterio_crs_works.__func__(),
        reason="rasterio CRS not functional (conflicting PROJ database)",
    )
    def test_export_3d_array(self, tmp_path):
        """Test exporting a 3D (multi-band) numpy array as GeoTIFF."""
        from rasterio.transform import from_bounds

        data = np.random.rand(3, 50, 50).astype(np.float32)
        transform = from_bounds(0, 0, 1, 1, 50, 50)
        out = tmp_path / "multi.tif"

        GeoExporter().to_geotiff(data, str(out), crs="EPSG:4326", transform=transform)

        import rasterio
        with rasterio.open(str(out)) as src:
            assert src.count == 3

    def test_geotiff_not_for_features(self, point_features, tmp_path):
        """Test that exporting vector features as GeoTIFF raises TypeError."""
        out = tmp_path / "bad.tif"
        with pytest.raises(TypeError, match="raster data"):
            GeoExporter().export(point_features, str(out), format="geotiff")


class TestShapefileExporter:
    """Test ESRI Shapefile export."""

    def test_export_points(self, point_features, tmp_path):
        """Test Shapefile export for point features."""
        import geopandas as gpd

        out = tmp_path / "points.shp"
        GeoExporter().to_shapefile(point_features, str(out))
        assert out.exists()

        gdf = gpd.read_file(str(out))
        assert len(gdf) == 4

    def test_export_empty_raises(self, tmp_path):
        """Test Shapefile export with empty list raises ValueError."""
        out = tmp_path / "empty.shp"
        with pytest.raises(ValueError, match="No features"):
            GeoExporter().to_shapefile([], str(out))


class TestGeoDataFrameBridge:
    """Test conversion to GeoDataFrame."""

    def test_to_geodataframe(self, point_features):
        """Test converting features to a GeoDataFrame."""
        exporter = GeoExporter()
        gdf = exporter.to_geodataframe(point_features)
        assert len(gdf) == 4
        assert "geometry" in gdf.columns
        assert gdf.crs is not None

    def test_to_geodataframe_empty(self):
        """Test converting empty list returns empty GeoDataFrame."""
        gdf = GeoExporter().to_geodataframe([])
        assert len(gdf) == 0

    def test_to_geodataframe_preserves_properties(self, point_features):
        """Test that feature properties are preserved."""
        gdf = GeoExporter().to_geodataframe(point_features)
        assert "id" in gdf.columns
        assert "value" in gdf.columns
        assert gdf.iloc[0]["value"] == 0
        assert gdf.iloc[1]["value"] == 10

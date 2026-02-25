"""Integration tests — end-to-end workflows combining multiple geo modules."""

import json
import pytest
from pathlib import Path
from shapely.geometry import Point, Polygon

from scrapling.geo.models import GeoPoint, GeoFeature, BoundingBox
from scrapling.geo.crs.manager import CRSManager
from scrapling.geo.parsers.coordinate import CoordinateExtractor
from scrapling.geo.parsers.geometry import GeometryParser
from scrapling.geo.exporters.base import GeoExporter
from scrapling.geo.validators.geometry import GeometryValidator
from scrapling.geo.validators.coordinates import CoordinateValidator
from scrapling.geo.storage.geopackage import GeoPackageStorage


class TestExtractTransformExport:
    """End-to-end: extract coordinates → transform CRS → validate → export."""

    def test_text_to_geojson(self, tmp_path):
        """Extract coords from text, transform, validate, and export to GeoJSON."""
        text = "Offices at 48.8566, 2.3522 and 52.5200, 13.4050"

        # 1. Extract
        extractor = CoordinateExtractor()
        points = extractor.extract_from_text(text)
        assert len(points) >= 2

        # 2. Create features
        features = [
            GeoFeature(geometry=p.to_shapely(), properties={"idx": i}, crs="EPSG:4326")
            for i, p in enumerate(points)
        ]

        # 3. Validate
        validator = GeometryValidator()
        for feat in features:
            valid, _ = validator.validate(feat.geometry)
            assert valid is True

        # 4. Export
        out = tmp_path / "offices.geojson"
        GeoExporter().export(features, str(out))
        assert out.exists()

        # 5. Verify
        data = json.loads(out.read_text())
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == len(features)

    def test_transform_export_geopackage(self, tmp_path):
        """Create features, transform to UTM, export to GeoPackage, re-read."""
        import geopandas as gpd

        # Create features in WGS84
        features_wgs84 = [
            GeoFeature(
                geometry=Point(-74.006, 40.7128),
                properties={"name": "NYC"},
                crs="EPSG:4326",
            ),
            GeoFeature(
                geometry=Point(-73.935, 40.730),
                properties={"name": "Brooklyn"},
                crs="EPSG:4326",
            ),
        ]

        # Transform to UTM 18N
        features_utm = [f.transform("EPSG:32618") for f in features_wgs84]
        assert all(f.crs == "EPSG:32618" for f in features_utm)

        # Export to GeoPackage
        gpkg_path = tmp_path / "cities.gpkg"
        GeoExporter(crs="EPSG:32618").to_geopackage(features_utm, str(gpkg_path))
        assert gpkg_path.exists()

        # Read back with geopandas
        gdf = gpd.read_file(str(gpkg_path))
        assert len(gdf) == 2
        assert "name" in gdf.columns


class TestGeoPackageRoundtrip:
    """End-to-end: save features → query → retrieve."""

    def test_save_and_query(self, tmp_path):
        """Save features to GeoPackage, query by bbox, verify results."""
        features = [
            GeoFeature(geometry=Point(-74.006, 40.7128), properties={"city": "NYC"}),
            GeoFeature(geometry=Point(-0.1276, 51.5074), properties={"city": "London"}),
            GeoFeature(geometry=Point(2.3522, 48.8566), properties={"city": "Paris"}),
        ]

        gpkg = tmp_path / "cities.gpkg"
        store = GeoPackageStorage(str(gpkg))
        store.save_features("cities", features)

        # Query for European cities only
        eu_results = store.query_bbox("cities", (-10, 40, 20, 60))
        eu_cities = [f.properties["city"] for f in eu_results]
        assert "London" in eu_cities
        assert "Paris" in eu_cities
        assert "NYC" not in eu_cities


class TestCRSPipeline:
    """Test CRS transformation pipeline across components."""

    def test_full_crs_pipeline(self):
        """Test WGS84 → UTM → back to WGS84 preserves coordinates."""
        mgr = CRSManager()
        original = [(-74.006, 40.7128)]

        # Forward
        utm_coords, utm_code = mgr.to_utm(original)
        assert utm_code.startswith("EPSG:326")

        # Backward
        wgs84_coords = mgr.to_wgs84(utm_coords, utm_code)
        assert wgs84_coords[0][0] == pytest.approx(original[0][0], abs=1e-6)
        assert wgs84_coords[0][1] == pytest.approx(original[0][1], abs=1e-6)

    def test_feature_transform_roundtrip(self):
        """Test GeoFeature CRS roundtrip preserves geometry."""
        original = GeoFeature(
            geometry=Polygon([(-74.1, 40.6), (-73.9, 40.6), (-73.9, 40.8), (-74.1, 40.8)]),
            properties={"name": "NYC area"},
            crs="EPSG:4326",
        )

        # WGS84 → UTM → WGS84
        utm = original.transform("EPSG:32618")
        back = utm.transform("EPSG:4326")

        assert back.geometry.centroid.x == pytest.approx(original.geometry.centroid.x, abs=1e-4)
        assert back.geometry.centroid.y == pytest.approx(original.geometry.centroid.y, abs=1e-4)


class TestMultiFormatExport:
    """Test exporting the same features to multiple formats."""

    def test_export_all_vector_formats(self, point_features, tmp_path):
        """Export features to GeoJSON, CSV, and GeoPackage and verify all."""
        exporter = GeoExporter()

        # GeoJSON
        gj_path = tmp_path / "out.geojson"
        exporter.export(point_features, str(gj_path))
        gj_data = json.loads(gj_path.read_text())
        assert len(gj_data["features"]) == 4

        # CSV
        csv_path = tmp_path / "out.csv"
        exporter.export(point_features, str(csv_path))
        lines = csv_path.read_text().splitlines()
        assert len(lines) == 6  # comment + header + 4 data

        # GeoPackage
        gpkg_path = tmp_path / "out.gpkg"
        exporter.export(point_features, str(gpkg_path))

        import geopandas as gpd
        gdf = gpd.read_file(str(gpkg_path))
        assert len(gdf) == 4


class TestCoordinateValidationPipeline:
    """Test coordinate extraction + validation pipeline."""

    def test_validate_extracted_coords(self):
        """Extract coordinates and validate them."""
        text = "Station at 40.7128, -74.0060 and outlier at 999.0, 999.0"

        extractor = CoordinateExtractor()
        points = extractor.extract_from_text(text)

        validator = CoordinateValidator()
        valid_points = []
        for p in points:
            ok, _ = validator.validate_lat_lon(p.y, p.x)
            if ok:
                valid_points.append(p)

        # The 999, 999 pair should not appear as a valid coordinate
        for p in valid_points:
            assert -90 <= p.y <= 90
            assert -180 <= p.x <= 180


class TestGeometryMeasurementPipeline:
    """Test geometry creation + measurement pipeline."""

    def test_points_to_polygon_area(self):
        """Create a polygon from GeoPoints and calculate its area."""
        parser = GeometryParser()

        # ~1km x ~1km square near the equator
        points = [
            GeoPoint(x=0, y=0),
            GeoPoint(x=0.01, y=0),
            GeoPoint(x=0.01, y=0.01),
            GeoPoint(x=0, y=0.01),
        ]
        poly = parser.points_to_polygon(points)
        area = parser.calculate_area(poly, crs="EPSG:4326")
        # ~1.24 km² (0.01° × 0.01° at equator)
        assert area == pytest.approx(1.24e6, rel=0.1)

    def test_distance_between_cities(self):
        """Calculate geodesic distance between known cities."""
        parser = GeometryParser()
        nyc = GeoPoint(x=-74.006, y=40.7128)
        london = GeoPoint(x=-0.1276, y=51.5074)
        paris = GeoPoint(x=2.3522, y=48.8566)

        nyc_london = parser.calculate_distance(nyc, london)
        london_paris = parser.calculate_distance(london, paris)

        # NYC-London ≈ 5,570 km
        assert nyc_london == pytest.approx(5_570_000, rel=0.02)
        # London-Paris ≈ 344 km
        assert london_paris == pytest.approx(344_000, rel=0.05)

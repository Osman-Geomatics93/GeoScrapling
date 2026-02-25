"""Tests for scrapling.geo.parsers — CoordinateExtractor, GeometryParser,
OGCResponseParser, SpatialMetadataParser.
"""

import json
import pytest
from shapely.geometry import Point, LineString, Polygon

from scrapling.geo.parsers.coordinate import CoordinateExtractor
from scrapling.geo.parsers.geometry import GeometryParser
from scrapling.geo.parsers.ogc import OGCResponseParser
from scrapling.geo.parsers.metadata import SpatialMetadataParser
from scrapling.geo.models import GeoPoint, GeoFeature


# ═══════════════════════════════════════════════════════════════════════════
# CoordinateExtractor
# ═══════════════════════════════════════════════════════════════════════════


class TestCoordinateExtractorText:
    """Test free-text coordinate extraction."""

    @pytest.fixture
    def extractor(self):
        return CoordinateExtractor()

    def test_extract_decimal_degrees(self, extractor, text_with_dd_coords):
        """Test extracting decimal degree pairs from text."""
        points = extractor.extract_from_text(text_with_dd_coords)
        assert len(points) >= 1
        p = points[0]
        assert p.y == pytest.approx(40.7128, abs=0.001)
        assert p.x == pytest.approx(-74.006, abs=0.001)

    def test_extract_dms(self, extractor, text_with_dms_coords):
        """Test extracting DMS coordinates from text."""
        points = extractor.extract_from_text(text_with_dms_coords)
        assert len(points) >= 1
        p = points[0]
        assert p.y == pytest.approx(40.7128, abs=0.01)
        assert abs(p.x) == pytest.approx(74.006, abs=0.01)

    def test_extract_utm(self, extractor, text_with_utm_coords):
        """Test extracting UTM coordinates from text."""
        points = extractor.extract_from_text(text_with_utm_coords)
        assert len(points) >= 1
        p = points[0]
        assert p.y == pytest.approx(40.7128, abs=0.1)

    def test_extract_empty_text(self, extractor):
        """Test extraction from empty text."""
        points = extractor.extract_from_text("")
        assert points == []

    def test_extract_no_coords(self, extractor):
        """Test extraction from text without coordinates."""
        points = extractor.extract_from_text("This is just a sentence.")
        assert points == []

    @pytest.mark.parametrize("text,expected_lat,expected_lon", [
        ("40.7128, -74.0060", 40.7128, -74.0060),
        ("51.5074, -0.1276", 51.5074, -0.1276),
        ("-33.8688, 151.2093", -33.8688, 151.2093),
    ])
    def test_extract_various_dd(self, extractor, text, expected_lat, expected_lon):
        """Test extracting various decimal degree formats."""
        points = extractor.extract_from_text(text)
        assert len(points) >= 1
        assert points[0].y == pytest.approx(expected_lat, abs=0.001)
        assert points[0].x == pytest.approx(expected_lon, abs=0.001)


class TestCoordinateExtractorDMS:
    """Test DMS parsing."""

    @pytest.mark.parametrize("dms_str,expected", [
        ("40°42'46\"N", 40.7128),
        ("74°00'22\"W", -74.006),
        ("51°30'26\"N", 51.5072),
        ("0°07'39\"W", -0.1275),
    ])
    def test_parse_dms(self, dms_str, expected):
        """Test parsing individual DMS strings."""
        result = CoordinateExtractor.parse_dms(dms_str)
        assert result == pytest.approx(expected, abs=0.01)

    def test_parse_dms_invalid(self):
        """Test parsing an invalid DMS string raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse DMS"):
            CoordinateExtractor.parse_dms("not a coordinate")


class TestCoordinateExtractorUTM:
    """Test UTM parsing."""

    def test_parse_utm(self):
        """Test parsing a UTM string to lat/lon."""
        lat, lon = CoordinateExtractor.parse_utm("18T 583960 4507523")
        assert lat == pytest.approx(40.7128, abs=0.1)
        assert lon == pytest.approx(-74.006, abs=0.1)

    def test_parse_utm_invalid(self):
        """Test parsing an invalid UTM string raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse UTM"):
            CoordinateExtractor.parse_utm("not a utm ref")


class TestCoordinateExtractorGeoJSON:
    """Test GeoJSON extraction."""

    @pytest.fixture
    def extractor(self):
        return CoordinateExtractor()

    def test_extract_feature_collection(self, extractor, sample_geojson_str):
        """Test extracting features from a GeoJSON FeatureCollection."""
        features = extractor.extract_from_geojson(sample_geojson_str)
        assert len(features) == 2
        assert isinstance(features[0], GeoFeature)
        assert features[0].properties["name"] == "New York"
        assert features[1].properties["name"] == "London"

    def test_extract_single_feature(self, extractor):
        """Test extracting a single GeoJSON Feature."""
        geojson = json.dumps({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": {"name": "Origin"},
        })
        features = extractor.extract_from_geojson(geojson)
        assert len(features) == 1
        assert features[0].geometry.geom_type == "Point"

    def test_extract_bare_geometry(self, extractor):
        """Test extracting a bare GeoJSON geometry (no Feature wrapper)."""
        geojson = json.dumps({"type": "Point", "coordinates": [10, 20]})
        features = extractor.extract_from_geojson(geojson)
        assert len(features) == 1
        assert features[0].geometry.x == pytest.approx(10)
        assert features[0].geometry.y == pytest.approx(20)


# ═══════════════════════════════════════════════════════════════════════════
# GeometryParser
# ═══════════════════════════════════════════════════════════════════════════


class TestGeometryParserParsing:
    """Test geometry parsing from various formats."""

    @pytest.fixture
    def parser(self):
        return GeometryParser()

    def test_parse_wkt_point(self, parser):
        """Test parsing WKT point."""
        geom = parser.parse_wkt("POINT (-74.006 40.7128)")
        assert geom.geom_type == "Point"
        assert geom.x == pytest.approx(-74.006)

    def test_parse_wkt_polygon(self, parser):
        """Test parsing WKT polygon."""
        geom = parser.parse_wkt("POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))")
        assert geom.geom_type == "Polygon"
        assert geom.is_valid

    def test_parse_wkb_roundtrip(self, parser, sample_point):
        """Test WKB roundtrip: Point -> WKB -> Point."""
        wkb = sample_point.wkb
        geom = parser.parse_wkb(wkb)
        assert geom.equals(sample_point)

    def test_parse_geojson_geometry(self, parser):
        """Test parsing a GeoJSON geometry dict."""
        gj = {"type": "Point", "coordinates": [-74.006, 40.7128]}
        geom = parser.parse_geojson_geometry(gj)
        assert geom.geom_type == "Point"
        assert geom.x == pytest.approx(-74.006)


class TestGeometryParserConstruction:
    """Test geometry construction from GeoPoints."""

    @pytest.fixture
    def parser(self):
        return GeometryParser()

    def test_points_to_line(self, parser):
        """Test creating a LineString from GeoPoints."""
        points = [GeoPoint(x=0, y=0), GeoPoint(x=1, y=1), GeoPoint(x=2, y=0)]
        line = parser.points_to_line(points)
        assert isinstance(line, LineString)
        assert len(line.coords) == 3

    def test_points_to_polygon(self, parser):
        """Test creating a Polygon from GeoPoints."""
        points = [GeoPoint(x=0, y=0), GeoPoint(x=1, y=0), GeoPoint(x=1, y=1), GeoPoint(x=0, y=1)]
        poly = parser.points_to_polygon(points)
        assert isinstance(poly, Polygon)
        assert poly.is_valid
        # Ring should be auto-closed
        assert len(poly.exterior.coords) == 5


class TestGeometryParserMeasurement:
    """Test geometry measurement methods."""

    @pytest.fixture
    def parser(self):
        return GeometryParser()

    def test_calculate_distance_geodesic(self, parser):
        """Test geodesic distance between two points."""
        p1 = GeoPoint(x=-74.006, y=40.7128)  # NYC
        p2 = GeoPoint(x=-0.1276, y=51.5074)  # London
        dist = parser.calculate_distance(p1, p2, method="geodesic")
        # NYC to London ≈ 5,570 km
        assert dist == pytest.approx(5_570_000, rel=0.02)

    def test_calculate_distance_euclidean(self, parser):
        """Test euclidean distance between two points."""
        p1 = GeoPoint(x=0, y=0)
        p2 = GeoPoint(x=3, y=4)
        dist = parser.calculate_distance(p1, p2, method="euclidean")
        assert dist == pytest.approx(5.0)

    def test_calculate_area_geographic(self, parser):
        """Test area calculation for a geographic polygon."""
        # ~1 degree x 1 degree polygon near equator
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        area = parser.calculate_area(poly, crs="EPSG:4326")
        # Area of 1°x1° at equator ≈ 1.24e10 m²
        assert area > 1e10

    def test_calculate_area_projected(self, parser):
        """Test area calculation for a projected polygon (in metres)."""
        # 100m x 100m square
        poly = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
        area = parser.calculate_area(poly, crs="EPSG:32618")
        assert area == pytest.approx(10000.0)


class TestGeometryParserManipulation:
    """Test geometry manipulation methods."""

    @pytest.fixture
    def parser(self):
        return GeometryParser()

    def test_simplify(self, parser):
        """Test geometry simplification."""
        # Complex polygon with many vertices
        coords = [(i * 0.01, (i % 3) * 0.01) for i in range(100)]
        coords.append(coords[0])
        poly = Polygon(coords)
        simplified = parser.simplify(poly, tolerance=0.05)
        assert len(simplified.exterior.coords) < len(poly.exterior.coords)

    def test_validate_valid(self, parser, sample_polygon):
        """Test validation of a valid geometry."""
        valid, errors = parser.validate(sample_polygon)
        assert valid is True
        assert errors == []

    def test_validate_invalid(self, parser, self_intersecting_polygon):
        """Test validation of an invalid geometry."""
        valid, errors = parser.validate(self_intersecting_polygon)
        assert valid is False
        assert len(errors) > 0

    def test_buffer_geographic(self, parser):
        """Test buffering a geographic point by metres."""
        point = Point(-74.006, 40.7128)
        buffered = parser.buffer(point, distance_m=1000, crs="EPSG:4326")
        assert buffered.geom_type == "Polygon"
        assert buffered.is_valid
        # Buffered geometry should be larger
        assert buffered.area > 0

    def test_buffer_projected(self, parser):
        """Test buffering a projected point by metres."""
        point = Point(500000, 5000000)
        buffered = parser.buffer(point, distance_m=100, crs="EPSG:32618")
        assert buffered.geom_type == "Polygon"
        # Area of 100m buffer circle ≈ π * 100² ≈ 31416
        assert buffered.area == pytest.approx(31416, rel=0.01)


# ═══════════════════════════════════════════════════════════════════════════
# OGCResponseParser
# ═══════════════════════════════════════════════════════════════════════════


class TestOGCResponseParserWMS:
    """Test WMS capabilities parsing."""

    @pytest.fixture
    def parser(self):
        return OGCResponseParser()

    def test_parse_wms_capabilities(self, parser, wms_capabilities_xml):
        """Test parsing WMS GetCapabilities."""
        caps = parser.parse_wms_capabilities(wms_capabilities_xml)
        assert caps["version"] == "1.3.0"
        assert caps["title"] == "Test WMS"
        assert caps["abstract"] == "A test WMS service"
        assert len(caps["layers"]) == 2

    def test_wms_layer_info(self, parser, wms_capabilities_xml):
        """Test layer metadata extraction from WMS capabilities."""
        caps = parser.parse_wms_capabilities(wms_capabilities_xml)
        layer = caps["layers"][0]
        assert layer["name"] == "test_layer"
        assert layer["title"] == "Test Layer"
        assert "EPSG:4326" in layer["crs"]
        assert "EPSG:3857" in layer["crs"]


class TestOGCResponseParserGML:
    """Test GML feature parsing."""

    @pytest.fixture
    def parser(self):
        return OGCResponseParser()

    def test_parse_gml_features(self, parser, gml_features_xml):
        """Test parsing GML feature members."""
        features = parser.parse_gml_features(gml_features_xml)
        assert len(features) == 2
        assert isinstance(features[0], GeoFeature)
        assert features[0].geometry.geom_type == "Point"

    def test_gml_feature_properties(self, parser, gml_features_xml):
        """Test properties are extracted from GML features."""
        features = parser.parse_gml_features(gml_features_xml)
        assert features[0].properties["name"] == "Park"
        assert features[1].properties["name"] == "Museum"

    def test_gml_feature_coordinates(self, parser, gml_features_xml):
        """Test coordinates are correctly parsed from GML."""
        features = parser.parse_gml_features(gml_features_xml)
        # GML coordinates format is x,y (lon,lat)
        pt = features[0].geometry
        assert pt.x == pytest.approx(-74.006, abs=0.01)
        assert pt.y == pytest.approx(40.7128, abs=0.01)


class TestOGCResponseParserCSW:
    """Test CSW record parsing."""

    @pytest.fixture
    def parser(self):
        return OGCResponseParser()

    def test_parse_empty_csw(self, parser):
        """Test parsing an empty CSW response."""
        xml = """<?xml version="1.0"?>
        <csw:GetRecordsResponse xmlns:csw="http://www.opengis.net/cat/csw/2.0.2">
          <csw:SearchResults numberOfRecordsMatched="0" numberOfRecordsReturned="0">
          </csw:SearchResults>
        </csw:GetRecordsResponse>"""
        records = parser.parse_csw_records(xml)
        assert records == []


# ═══════════════════════════════════════════════════════════════════════════
# SpatialMetadataParser
# ═══════════════════════════════════════════════════════════════════════════


class TestSpatialMetadataParser:
    """Test ISO 19115 and Dublin Core metadata parsing."""

    @pytest.fixture
    def parser(self):
        return SpatialMetadataParser()

    def test_parse_iso19115(self, parser, iso19115_xml):
        """Test parsing ISO 19115 metadata."""
        meta = parser.parse_iso19115(iso19115_xml)
        assert meta["file_identifier"] == "test-dataset-001"
        assert meta["language"] == "eng"
        assert meta["date_stamp"] == "2024-01-15"
        assert meta["title"] == "Test Geospatial Dataset"
        assert meta["abstract"] == "A sample metadata record for testing"

    def test_iso19115_bbox(self, parser, iso19115_xml):
        """Test bounding box extraction from ISO 19115."""
        meta = parser.parse_iso19115(iso19115_xml)
        bbox = meta.get("bbox")
        assert bbox is not None
        assert bbox["west"] == pytest.approx(-74.3)
        assert bbox["east"] == pytest.approx(-73.7)
        assert bbox["south"] == pytest.approx(40.5)
        assert bbox["north"] == pytest.approx(40.9)

    def test_parse_dublin_core(self, parser):
        """Test parsing Dublin Core metadata."""
        xml = """<?xml version="1.0"?>
        <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
          <dc:title>Test Dataset</dc:title>
          <dc:creator>Test Author</dc:creator>
          <dc:subject>Geospatial</dc:subject>
          <dc:description>A test dataset</dc:description>
        </metadata>"""
        meta = parser.parse_dublin_core(xml)
        assert meta.get("title") == "Test Dataset"
        assert meta.get("creator") == "Test Author"

"""Shared fixtures for GeoScrapling tests."""

import pytest
from shapely.geometry import Point, LineString, Polygon, box, MultiPoint

from scrapling.geo.models import GeoPoint, GeoFeature, BoundingBox, CoordinateQuality


# ── Coordinate fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def wgs84_point():
    """A WGS84 point in New York City."""
    return GeoPoint(x=-74.006, y=40.7128, crs="EPSG:4326")


@pytest.fixture
def utm_point():
    """A UTM zone 18N point (same location as wgs84_point, approx.)."""
    return GeoPoint(x=583960.0, y=4507523.0, crs="EPSG:32618")


@pytest.fixture
def london_point():
    """A WGS84 point in London."""
    return GeoPoint(x=-0.1276, y=51.5074, crs="EPSG:4326")


@pytest.fixture
def point_with_elevation():
    """A 3D point with elevation."""
    return GeoPoint(x=13.4050, y=52.5200, z=34.0, crs="EPSG:4326")


@pytest.fixture
def sample_quality():
    """A CoordinateQuality instance."""
    return CoordinateQuality(
        precision=6,
        accuracy_m=1.5,
        source="gps",
        method="rtk",
        confidence=0.95,
        crs="EPSG:4326",
    )


# ── Geometry fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def sample_polygon():
    """A simple square polygon."""
    return Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])


@pytest.fixture
def sample_linestring():
    """A simple LineString."""
    return LineString([(0, 0), (1, 1), (2, 0)])


@pytest.fixture
def sample_point():
    """A Shapely Point."""
    return Point(-74.006, 40.7128)


@pytest.fixture
def self_intersecting_polygon():
    """A polygon with a self-intersection (bowtie shape)."""
    return Polygon([(0, 0), (2, 2), (2, 0), (0, 2), (0, 0)])


# ── Feature fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def sample_feature(sample_polygon):
    """A GeoFeature with a polygon geometry."""
    return GeoFeature(
        geometry=sample_polygon,
        properties={"name": "Test Polygon", "area_code": 42},
        crs="EPSG:4326",
        id="feat-001",
    )


@pytest.fixture
def sample_features(sample_polygon, sample_linestring, sample_point):
    """A list of mixed GeoFeatures."""
    return [
        GeoFeature(geometry=sample_polygon, properties={"name": "Polygon"}, id="1"),
        GeoFeature(geometry=sample_linestring, properties={"name": "Line"}, id="2"),
        GeoFeature(geometry=sample_point, properties={"name": "Point"}, id="3"),
    ]


@pytest.fixture
def point_features():
    """A list of GeoFeatures with Point geometries."""
    return [
        GeoFeature(geometry=Point(lon, lat), properties={"id": i, "value": i * 10})
        for i, (lon, lat) in enumerate([
            (-74.006, 40.7128),
            (-0.1276, 51.5074),
            (2.3522, 48.8566),
            (13.4050, 52.5200),
        ])
    ]


# ── BoundingBox fixtures ───────────────────────────────────────────────────


@pytest.fixture
def nyc_bbox():
    """Bounding box around New York City."""
    return BoundingBox(min_x=-74.3, min_y=40.5, max_x=-73.7, max_y=40.9)


@pytest.fixture
def world_bbox():
    """Bounding box covering the whole world."""
    return BoundingBox(min_x=-180, min_y=-90, max_x=180, max_y=90)


# ── Text / HTML fixtures ───────────────────────────────────────────────────


@pytest.fixture
def text_with_dd_coords():
    """Text containing decimal degree coordinates."""
    return "The location is at 40.7128, -74.0060 in New York City."


@pytest.fixture
def text_with_dms_coords():
    """Text containing DMS coordinates."""
    return "Station at 40°42'46\"N 74°00'22\"W near the harbor."


@pytest.fixture
def text_with_utm_coords():
    """Text containing UTM coordinates."""
    return "Grid reference: 18T 583960 4507523"


@pytest.fixture
def html_with_geo_meta():
    """HTML with geo meta tags and JSON-LD."""
    return """<!DOCTYPE html>
<html>
<head>
    <meta name="geo.position" content="40.7128;-74.006">
    <meta property="place:location:latitude" content="40.7128">
    <meta property="place:location:longitude" content="-74.006">
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Place",
        "geo": {
            "@type": "GeoCoordinates",
            "latitude": 40.7128,
            "longitude": -74.006
        }
    }
    </script>
</head>
<body>
    <p>Visit us at 40.7128, -74.006</p>
</body>
</html>"""


@pytest.fixture
def sample_geojson_str():
    """A GeoJSON FeatureCollection as a string."""
    import json
    return json.dumps({
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "1",
                "geometry": {"type": "Point", "coordinates": [-74.006, 40.7128]},
                "properties": {"name": "New York"},
            },
            {
                "type": "Feature",
                "id": "2",
                "geometry": {"type": "Point", "coordinates": [-0.1276, 51.5074]},
                "properties": {"name": "London"},
            },
        ],
    })


# ── OGC / XML fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def wms_capabilities_xml():
    """Minimal WMS GetCapabilities XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<WMS_Capabilities version="1.3.0">
  <Service>
    <Title>Test WMS</Title>
    <Abstract>A test WMS service</Abstract>
  </Service>
  <Capability>
    <Layer>
      <Name>test_layer</Name>
      <Title>Test Layer</Title>
      <CRS>EPSG:4326</CRS>
      <CRS>EPSG:3857</CRS>
    </Layer>
    <Layer>
      <Name>another_layer</Name>
      <Title>Another Layer</Title>
      <CRS>EPSG:4326</CRS>
    </Layer>
  </Capability>
</WMS_Capabilities>"""


@pytest.fixture
def gml_features_xml():
    """Minimal GML with feature members."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs"
                       xmlns:gml="http://www.opengis.net/gml">
  <gml:featureMember>
    <Feature>
      <name>Park</name>
      <gml:Point>
        <gml:coordinates>-74.006,40.7128</gml:coordinates>
      </gml:Point>
    </Feature>
  </gml:featureMember>
  <gml:featureMember>
    <Feature>
      <name>Museum</name>
      <gml:Point>
        <gml:coordinates>-73.963,40.779</gml:coordinates>
      </gml:Point>
    </Feature>
  </gml:featureMember>
</wfs:FeatureCollection>"""


@pytest.fixture
def iso19115_xml():
    """Minimal ISO 19115 metadata XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                 xmlns:gco="http://www.isotc211.org/2005/gco">
  <gmd:fileIdentifier>
    <gco:CharacterString>test-dataset-001</gco:CharacterString>
  </gmd:fileIdentifier>
  <gmd:language>
    <gco:CharacterString>eng</gco:CharacterString>
  </gmd:language>
  <gmd:dateStamp>
    <gco:Date>2024-01-15</gco:Date>
  </gmd:dateStamp>
  <gmd:identificationInfo>
    <gmd:MD_DataIdentification>
      <gmd:citation>
        <gmd:CI_Citation>
          <gmd:title>
            <gco:CharacterString>Test Geospatial Dataset</gco:CharacterString>
          </gmd:title>
        </gmd:CI_Citation>
      </gmd:citation>
      <gmd:abstract>
        <gco:CharacterString>A sample metadata record for testing</gco:CharacterString>
      </gmd:abstract>
      <gmd:extent>
        <gmd:EX_Extent>
          <gmd:geographicElement>
            <gmd:EX_GeographicBoundingBox>
              <gmd:westBoundLongitude><gco:Decimal>-74.3</gco:Decimal></gmd:westBoundLongitude>
              <gmd:eastBoundLongitude><gco:Decimal>-73.7</gco:Decimal></gmd:eastBoundLongitude>
              <gmd:southBoundLatitude><gco:Decimal>40.5</gco:Decimal></gmd:southBoundLatitude>
              <gmd:northBoundLatitude><gco:Decimal>40.9</gco:Decimal></gmd:northBoundLatitude>
            </gmd:EX_GeographicBoundingBox>
          </gmd:geographicElement>
        </gmd:EX_Extent>
      </gmd:extent>
    </gmd:MD_DataIdentification>
  </gmd:identificationInfo>
</gmd:MD_Metadata>"""

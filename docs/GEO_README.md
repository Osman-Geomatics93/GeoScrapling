<div align="center">

<h1>GeoScrapling</h1>
<h3>Geospatial Intelligence for Web Scraping</h3>

<p>
    <a href="https://github.com/Osman-Geomatics93/GeoScrapling/actions/workflows/geo-tests.yml">
        <img alt="Geo Tests" src="https://img.shields.io/github/actions/workflow/status/Osman-Geomatics93/GeoScrapling/geo-tests.yml?style=for-the-badge&logo=githubactions&logoColor=white&label=Geo%20Tests"></a>
    &nbsp;
    <a href="https://github.com/Osman-Geomatics93/GeoScrapling">
        <img alt="Code Quality" src="https://img.shields.io/badge/Code_Quality-A-brightgreen?style=for-the-badge&logo=codeclimate&logoColor=white"></a>
    &nbsp;
    <a href="https://github.com/Osman-Geomatics93/GeoScrapling/blob/main/LICENSE">
        <img alt="License" src="https://img.shields.io/github/license/Osman-Geomatics93/GeoScrapling?style=for-the-badge&logo=opensourceinitiative&logoColor=white"></a>
    &nbsp;
    <a href="https://pypi.org/project/scrapling/">
        <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white"></a>
</p>

<!-- Stats Bar -->
<p>
    <img alt="EPSG Codes" src="https://img.shields.io/badge/9,000+_EPSG_Codes-informational?style=flat-square&logo=openstreetmap&logoColor=white">
    &nbsp;
    <img alt="Export Formats" src="https://img.shields.io/badge/8_Export_Formats-informational?style=flat-square&logo=files&logoColor=white">
    &nbsp;
    <img alt="CLI Commands" src="https://img.shields.io/badge/10_CLI_Commands-informational?style=flat-square&logo=gnubash&logoColor=white">
    &nbsp;
    <img alt="Geo Tests" src="https://img.shields.io/badge/188_Geo_Tests-informational?style=flat-square&logo=pytest&logoColor=white">
    &nbsp;
    <img alt="LOC" src="https://img.shields.io/badge/4,500+_LOC-informational?style=flat-square&logo=codeclimate&logoColor=white">
</p>

<!-- Navigation -->
<p>
    <a href="#why-geoscrapling"><strong>Why GeoScrapling?</strong></a>
    &middot;
    <a href="#installation"><strong>Installation</strong></a>
    &middot;
    <a href="#quick-start"><strong>Quick Start</strong></a>
    &middot;
    <a href="#key-features"><strong>Features</strong></a>
    &middot;
    <a href="#cli-commands"><strong>CLI</strong></a>
    &middot;
    <a href="#architecture"><strong>Architecture</strong></a>
</p>

</div>

---

## Why GeoScrapling?

> Geomatics and geoinformatics professionals routinely need to harvest spatial data from the web — whether it's scraping coordinate lists from government portals, pulling features from OGC services, or extracting geo-tagged metadata from HTML pages. Existing tools force you to glue together a web scraper, a coordinate parser, a CRS library, and a spatial exporter. **GeoScrapling unifies all of this into a single pipeline**: fetch a page, extract coordinates, transform them, validate geometries, and export to any spatial format — in a few lines of Python.

---

**GeoScrapling** is a geospatial extension for the [Scrapling](https://github.com/D4Vinci/Scrapling) web-scraping framework. It adds coordinate extraction, CRS transformations, OGC web-service clients, multi-format export, spatial storage, and a geo-aware spider pipeline — giving geomatics, geoinformatics, and surveying professionals a single toolkit for harvesting, transforming, and storing spatial data from the web.

---

## Installation

```bash
pip install scrapling[geo]
```

> [!NOTE]
> This pulls in `pyproj`, `shapely`, `geopandas`, `fiona`, `rasterio`, `owslib`, `geojson`, `folium`, `fastkml`, `numpy`, and `click`.

---

## Quick Start

### Extract coordinates from text

```python
from scrapling.geo import CoordinateExtractor

extractor = CoordinateExtractor()
points = extractor.extract_from_text("""
    The summit is at 27°59'17"N 86°55'31"E (8848m).
    Base camp: 28.0025, 86.8528
""")

for pt in points:
    print(f"{pt.y:.4f}, {pt.x:.4f} — {pt.quality.method}")
# 27.9881, 86.9253 — dms
# 28.0025, 86.8528 — dd
```

### Fetch WFS features from an OGC service

```python
from scrapling.geo import OGCFetcher

fetcher = OGCFetcher("https://example.com/wfs", service_type="WFS")
gdf = fetcher.get_features("buildings", max_features=500)
print(f"{len(gdf)} features, CRS: {gdf.crs}")
```

### Export to multiple formats

```python
from scrapling.geo import GeoExporter, GeoFeature
from shapely.geometry import Point

features = [
    GeoFeature(geometry=Point(31.2357, 30.0444), properties={"name": "Cairo"}),
    GeoFeature(geometry=Point(36.8219, -1.2921), properties={"name": "Nairobi"}),
]

exporter = GeoExporter()
exporter.export(features, "cities.geojson")     # GeoJSON
exporter.export(features, "cities.shp")          # Shapefile
exporter.export(features, "cities.kml")          # KML
exporter.export(features, "cities.gpkg")         # GeoPackage
```

---

## Key Features

### Coordinate Extraction

Parse coordinates from any source — free text, HTML pages, or structured geospatial formats.

**Supported formats:** Decimal Degrees (DD), Degrees-Minutes-Seconds (DMS), Degrees-Decimal Minutes (DDM), UTM, MGRS, Geohash, HTML meta tags (`geo.position`, Open Graph), JSON-LD `GeoCoordinates`, KML, GeoJSON, GML.

```python
from scrapling.geo import CoordinateExtractor

extractor = CoordinateExtractor()

# From free text
points = extractor.extract_from_text("UTM 18T 583960 4507523")

# From HTML (Scrapling Selector)
points = extractor.extract_from_html(selector)

# From structured formats
features = extractor.extract_from_kml(kml_string)
features = extractor.extract_from_geojson(geojson_string)
features = extractor.extract_from_gml(gml_string)

# Parse individual formats
lat = extractor.parse_dms("""40°42'46"N""")
lat, lon = extractor.parse_utm("18T 583960 4507523")
lat, lon = extractor.parse_mgrs("18TWL8396007523")
```

---

### CRS Engine

Transform coordinates between 9,000+ EPSG codes with automatic UTM zone detection, datum shifts, and geoid height queries.

```python
from scrapling.geo import CRSManager

crs = CRSManager()

# Transform between any CRS
coords = crs.transform(
    [(583960, 4507523)],
    from_crs="EPSG:32618",  # UTM 18N
    to_crs="EPSG:4326"      # WGS84
)

# Auto-detect UTM zone
utm_coords, utm_epsg = crs.to_utm([(-74.006, 40.7128)])
print(utm_epsg)  # EPSG:32618

# Datum transformation
nad27 = crs.datum_transform(
    [(-74.006, 40.7128)], from_datum="NAD83", to_datum="NAD27"
)

# Geoid height & orthometric conversion
geoid_h = crs.get_geoid_height(40.7128, -74.006)
ortho_h = crs.ellipsoidal_to_orthometric(40.7128, -74.006, h_ellipsoidal=30.0)
```

**CRS Registry** with built-in aliases for common grids:

```python
from scrapling.geo import CRSRegistry

registry = CRSRegistry()
epsg = registry.resolve("OSGB36")     # "EPSG:27700"
epsg = registry.resolve("Web Mercator")  # "EPSG:3857"
results = registry.search("Swiss")    # [{name: "Swiss CH1903+", code: "EPSG:2056"}]
```

---

### OGC Services

A unified client for **WFS**, **WMS**, **WCS**, **WMTS**, and **CSW** services.

```python
from scrapling.geo import OGCFetcher

# WFS — vector features
wfs = OGCFetcher("https://example.com/wfs", service_type="WFS")
gdf = wfs.get_features("parcels", bbox=(10, 50, 11, 51), max_features=1000)

# WMS — rendered map images
wms = OGCFetcher("https://example.com/wms", service_type="WMS")
img = wms.get_map(layers=["topo"], bbox=(10, 50, 11, 51), size=(800, 600))

# WCS — raster coverage
wcs = OGCFetcher("https://example.com/wcs", service_type="WCS")
data = wcs.get_coverage("dem", bbox=(10, 50, 11, 51))

# WMTS — map tiles
wmts = OGCFetcher("https://example.com/wmts", service_type="WMTS")
tile = wmts.get_tile("satellite", zoom=14, row=8192, col=8192)

# CSW — catalogue search
csw = OGCFetcher("https://example.com/csw", service_type="CSW")
records = csw.search_catalog(keywords=["elevation"], max_records=50)

# Service discovery
layers = wfs.list_layers()
info = wfs.get_layer_info("parcels")
```

---

### Multi-Format Export

Export `GeoFeature` lists to any supported format. The format is auto-detected from the file extension.

| Format | Extension | Method |
|---|---|---|
| GeoJSON | `.geojson` | `to_geojson()` |
| Shapefile | `.shp` | `to_shapefile()` |
| KML | `.kml` | `to_kml()` |
| KMZ | `.kmz` | `to_kmz()` |
| GML | `.gml` | `to_gml()` |
| GeoPackage | `.gpkg` | `to_geopackage()` |
| GeoTIFF | `.tif` | `to_geotiff()` |
| CSV | `.csv` | `to_csv()` |

```python
from scrapling.geo import GeoExporter

exporter = GeoExporter()

# Auto-detect from extension
exporter.export(features, "output.geojson")
exporter.export(features, "output.shp")

# Or call format-specific methods
exporter.to_kml(features, "output.kml")
exporter.to_csv(features, "output.csv", coord_columns=("lon", "lat"))

# Convert to GeoDataFrame (no file output)
gdf = exporter.to_geodataframe(features)
```

---

### GeoSpider

A geo-aware spider extending `scrapling.spiders.Spider` with automatic CRS transformation, geometry validation, spatial filtering, and export on completion.

```python
from scrapling.geo import GeoSpider
from scrapling.spiders import Response

class SurveySpider(GeoSpider):
    name = "survey"
    start_urls = ["https://data.example.com/stations"]

    default_crs = "EPSG:4326"
    output_crs = "EPSG:32637"      # UTM 37N
    output_format = "geojson"
    output_path = "stations.geojson"
    validate_geometries = True
    bbox = (34.0, 29.0, 36.0, 31.5) # spatial filter

    async def parse(self, response: Response):
        # extract_coordinates() pulls all coords from the page
        points = self.extract_coordinates(response)
        for pt in points:
            yield self.create_feature(
                geometry=pt.to_shapely(),
                properties={"source": response.url},
            )
        # on_close() auto-exports to output_path

SurveySpider().start()
```

**Specialized spiders:** `OGCSpider`, `GeoportalSpider`, `SentinelSpider`, `CadastralSpider`.

---

### Spatial Storage

Persist features to spatial databases with automatic table creation and CRS management.

```python
from scrapling.geo import GeoPackageStorage, PostGISStorage, SpatiaLiteStorage

# GeoPackage (file-based, no server needed)
gpkg = GeoPackageStorage("survey.gpkg")
gpkg.store(features, layer="control_points")

# PostGIS
pg = PostGISStorage("postgresql://user:pass@localhost/geodb")
pg.store(features, table="parcels", srid=4326)

# SpatiaLite
sl = SpatiaLiteStorage("survey.db")
sl.store(features, table="monuments")
```

---

### Specialized Fetchers

Domain-specific data fetchers for common geospatial data sources.

```python
from scrapling.geo import ElevationFetcher, SatelliteFetcher, GNSSFetcher, CadastralFetcher

# Elevation queries, profiles, and DEM downloads
elev = ElevationFetcher()
height = elev.get_elevation(30.0444, 31.2357)
profile = elev.get_elevation_profile(line, samples=200)

# Satellite imagery metadata
sat = SatelliteFetcher()

# GNSS reference station data
gnss = GNSSFetcher()

# Cadastral / land parcel services
cadastral = CadastralFetcher()
```

---

### Validators

Validate coordinates, geometry topology, and spatial data quality.

```python
from scrapling.geo import CoordinateValidator, GeometryValidator

# Coordinate validation
cv = CoordinateValidator()
valid, errors = cv.validate_lat_lon(91.0, 0.0)  # (False, ["Latitude out of range"])
valid, errors = cv.validate_utm(583960, 4507523, zone=18)
on_land = cv.check_on_land(30.0444, 31.2357)

# Geometry validation & repair
gv = GeometryValidator()
valid, errors = gv.validate(polygon)
fixed = gv.fix_topology(invalid_polygon)
has_self_ix = gv.check_self_intersection(polygon)
ccw = gv.check_winding_order(polygon)  # RFC 7946
```

---

## CLI Commands

All commands are available under `scrapling geo`:

| Command | Description |
|---|---|
| `scrapling geo capabilities <url>` | Probe OGC service capabilities |
| `scrapling geo features <wfs_url> <layer>` | Download WFS features (`-o`, `-n`) |
| `scrapling geo convert <input> <output>` | Convert between geospatial formats (`--crs`) |
| `scrapling geo transform <file> <crs>` | Reproject a geospatial file (`-o`) |
| `scrapling geo validate <file>` | Validate geometries in a file |
| `scrapling geo extract-coords <url>` | Extract coordinates from a webpage |
| `scrapling geo elevation <lat> <lon>` | Query elevation at a point |
| `scrapling geo preview <file>` | Open Folium map preview in browser |
| `scrapling geo search <csw_url> <keyword>` | Search CSW catalogue (`-n`) |
| `scrapling geo tiles <wmts_url> <bbox>` | Download WMTS tiles (`-l`, `-z`, `-o`) |

```bash
# Download WFS parcels and convert to Shapefile
scrapling geo features https://example.com/wfs parcels -o parcels.geojson -n 5000
scrapling geo convert parcels.geojson parcels.shp --crs EPSG:32637

# Validate, preview, query elevation
scrapling geo validate parcels.shp
scrapling geo preview parcels.shp
scrapling geo elevation 30.0444 31.2357
```

---

## Data Models

Three core dataclasses power all geo operations:

```python
from scrapling.geo import GeoPoint, GeoFeature, BoundingBox

# GeoPoint — a coordinate with optional elevation & quality metadata
pt = GeoPoint(x=31.2357, y=30.0444, z=75.0, crs="EPSG:4326")
pt_wgs = pt.to_wgs84()
shapely_pt = pt.to_shapely()

# GeoFeature — geometry + properties (like a GeoJSON Feature)
feature = GeoFeature(
    geometry=pt.to_shapely(),
    properties={"name": "Cairo Tower", "height_m": 187},
    crs="EPSG:4326",
    id="tower-001",
)
geojson_dict = feature.to_geojson()
reprojected = feature.transform("EPSG:32636")

# BoundingBox — axis-aligned spatial extent
bbox = BoundingBox(min_x=31.0, min_y=29.5, max_x=31.5, max_y=30.5)
bbox.contains(pt)          # True
polygon = bbox.to_polygon()
bbox_utm = bbox.transform("EPSG:32636")
```

Each model carries a `crs` field (default `EPSG:4326`) and supports `CoordinateQuality` metadata for tracking precision, accuracy, source, and confidence.

---

## Architecture

<details>
<summary><strong>Module Structure</strong></summary>

```
scrapling/geo/
├── __init__.py              # Lazy public API (22 exports)
├── models.py                # GeoPoint, GeoFeature, BoundingBox, CoordinateQuality
├── cli.py                   # 10 CLI commands under `scrapling geo`
├── crs/
│   ├── manager.py           # CRSManager — transforms, datum shifts, geoid
│   ├── registry.py          # CRSRegistry — EPSG look-up, aliases, caching
│   └── quality.py           # Precision & accuracy estimation helpers
├── parsers/
│   ├── coordinate.py        # CoordinateExtractor — DD/DMS/UTM/MGRS/HTML/KML/GML
│   ├── geometry.py          # GeometryParser — WKT/WKB, area, distance, buffer
│   ├── ogc.py               # OGCResponseParser — WFS/WMS/WCS/WMTS/CSW responses
│   └── metadata.py          # SpatialMetadataParser
├── fetchers/
│   ├── ogc.py               # OGCFetcher — unified WFS/WMS/WCS/WMTS/CSW client
│   ├── elevation.py         # ElevationFetcher — DEM, slope, aspect
│   ├── satellite.py         # SatelliteFetcher
│   ├── gnss.py              # GNSSFetcher
│   └── cadastral.py         # CadastralFetcher
├── exporters/
│   ├── base.py              # GeoExporter — unified export interface
│   ├── geojson_exp.py       # GeoJSON exporter
│   ├── shapefile_exp.py     # Shapefile exporter
│   ├── kml_exp.py           # KML/KMZ exporter
│   ├── gml_exp.py           # GML exporter
│   ├── geopackage_exp.py    # GeoPackage exporter
│   ├── geotiff_exp.py       # GeoTIFF exporter
│   ├── geopandas_exp.py     # GeoDataFrame converter
│   └── csv_exp.py           # CSV with coordinates
├── spiders/
│   ├── base.py              # GeoSpider — geo-aware spider pipeline
│   ├── ogc_spider.py        # OGCSpider
│   ├── geoportal.py         # GeoportalSpider
│   ├── sentinel.py          # SentinelSpider
│   └── cadastral.py         # CadastralSpider
├── storage/
│   ├── geopackage.py        # GeoPackageStorage
│   ├── postgis.py           # PostGISStorage
│   └── spatialite.py        # SpatiaLiteStorage
├── validators/
│   ├── coordinates.py       # CoordinateValidator
│   └── geometry.py          # GeometryValidator
└── utils/
    ├── bbox.py              # Bounding-box helpers
    ├── projections.py        # Projection utilities
    └── units.py             # Unit conversion
```

**45 source files &middot; 4,500+ lines of code &middot; 8 test modules &middot; 188 tests**

</details>

---

<details>
<summary><strong>Dependency Details</strong></summary>

The `geo` extra installs the following packages:

| Package | Version | Purpose |
|---|---|---|
| `pyproj` | &ge; 3.6.0 | CRS transformations and datum operations |
| `shapely` | &ge; 2.0.0 | Geometry creation, validation, and analysis |
| `fiona` | &ge; 1.9.0 | Vector format I/O (Shapefile, GML, etc.) |
| `rasterio` | &ge; 1.3.0 | Raster format I/O (GeoTIFF, DEM) |
| `geopandas` | &ge; 0.14.0 | GeoDataFrame operations and spatial joins |
| `owslib` | &ge; 0.31.0 | OGC web-service client (WFS, WMS, etc.) |
| `geojson` | &ge; 3.1.0 | GeoJSON serialization and validation |
| `folium` | &ge; 0.15.0 | Interactive map preview generation |
| `fastkml` | &ge; 1.0 | KML/KMZ reading and writing |
| `numpy` | &ge; 1.24.0 | Numerical arrays for raster operations |
| `click` | &ge; 8.3.0 | CLI command framework |

</details>

---

## Testing

> [!TIP]
> Run individual test modules to speed up development iteration. The full suite covers models, CRS, parsers, validators, exporters, storage, integration, and utilities.

```bash
# All 188 geo tests
python -m pytest tests/geo/ -v

# Individual modules
python -m pytest tests/geo/test_models.py -v
python -m pytest tests/geo/test_crs.py -v
python -m pytest tests/geo/test_parsers.py -v
python -m pytest tests/geo/test_validators.py -v
python -m pytest tests/geo/test_exporters.py -v
python -m pytest tests/geo/test_storage.py -v
python -m pytest tests/geo/test_integration.py -v
python -m pytest tests/geo/test_utils.py -v
```

---

## License

BSD-3-Clause — same as the parent [Scrapling](https://github.com/D4Vinci/Scrapling) project.

---

<p align="center">
    <strong><a href="../README.md">&larr; Back to main README</a></strong>
</p>

<div align="center">

<h1>GeoScrapling</h1>
<h3>Geospatial Intelligence meets Web Scraping</h3>

<p>
    <a href="https://github.com/Osman-Geomatics93/GeoScrapling/actions/workflows/tests.yml">
        <img alt="Tests" src="https://img.shields.io/github/actions/workflow/status/Osman-Geomatics93/GeoScrapling/tests.yml?style=for-the-badge&logo=githubactions&logoColor=white&label=Tests"></a>
    &nbsp;
    <a href="https://github.com/Osman-Geomatics93/GeoScrapling/actions/workflows/geo-tests.yml">
        <img alt="Geo Tests" src="https://img.shields.io/github/actions/workflow/status/Osman-Geomatics93/GeoScrapling/geo-tests.yml?style=for-the-badge&logo=githubactions&logoColor=white&label=Geo%20Tests"></a>
    &nbsp;
    <a href="https://github.com/Osman-Geomatics93/GeoScrapling">
        <img alt="Code Quality" src="https://img.shields.io/badge/Code_Quality-A-brightgreen?style=for-the-badge&logo=codeclimate&logoColor=white"></a>
</p>

<p>
    <a href="https://github.com/Osman-Geomatics93/GeoScrapling/blob/main/LICENSE">
        <img alt="License" src="https://img.shields.io/github/license/Osman-Geomatics93/GeoScrapling?style=for-the-badge&logo=opensourceinitiative&logoColor=white"></a>
    &nbsp;
    <a href="https://pypi.org/project/scrapling/">
        <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white"></a>
    &nbsp;
    <img alt="Version" src="https://img.shields.io/badge/Version-0.4-blue?style=for-the-badge&logo=semver&logoColor=white">
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
    <a href="#-geospatial-intelligence"><strong>Geospatial</strong></a>
    &middot;
    <a href="#-web-scraping"><strong>Web Scraping</strong></a>
    &middot;
    <a href="#-installation"><strong>Installation</strong></a>
    &middot;
    <a href="#-cli--interactive-shell"><strong>CLI</strong></a>
    &middot;
    <a href="docs/GEO_README.md"><strong>Full Geo Docs</strong></a>
</p>

</div>

---

## Why GeoScrapling?

Geomatics and geoinformatics professionals routinely need to harvest spatial data from the web — scraping coordinate lists from government portals, pulling features from OGC services, or extracting geo-tagged metadata from HTML pages. Existing tools force you to glue together a web scraper, a coordinate parser, a CRS library, and a spatial exporter. **GeoScrapling unifies all of this into a single pipeline**: fetch a page, extract coordinates, transform CRS, validate geometries, and export to any spatial format — in a few lines of Python.

> [!TIP]
> GeoScrapling inherits **all** of Scrapling's strengths — adaptive parsing, anti-bot bypass, spider framework, MCP server, interactive shell — and layers professional-grade geospatial capabilities on top.

```python
from scrapling.fetchers import StealthyFetcher
from scrapling.geo import CoordinateExtractor, GeoExporter, GeoFeature

# Scrape a page and extract coordinates in one pipeline
page = StealthyFetcher.fetch('https://example.com/locations', headless=True)
extractor = CoordinateExtractor()
points = extractor.extract_from_html(page)

features = [GeoFeature(geometry=pt.to_shapely(), properties={"src": page.url}) for pt in points]
GeoExporter().export(features, "locations.geojson")
```

---

## Feature Grid

<table>
<tr>
    <td align="center" width="25%">
        <h4>Coordinate Extraction</h4>
        <p>Parse DD, DMS, UTM, MGRS, Geohash from text, HTML, KML, GeoJSON, and GML</p>
    </td>
    <td align="center" width="25%">
        <h4>CRS Engine</h4>
        <p>Transform between 9,000+ EPSG codes with auto UTM detection and datum shifts</p>
    </td>
    <td align="center" width="25%">
        <h4>OGC Services</h4>
        <p>Unified client for WFS, WMS, WCS, WMTS, and CSW web services</p>
    </td>
    <td align="center" width="25%">
        <h4>Multi-Format Export</h4>
        <p>Export to GeoJSON, Shapefile, KML, KMZ, GML, GeoPackage, GeoTIFF, and CSV</p>
    </td>
</tr>
<tr>
    <td align="center">
        <h4>GeoSpider Pipeline</h4>
        <p>Scrape-to-spatial pipeline with CRS transform, validation, and auto-export</p>
    </td>
    <td align="center">
        <h4>Spatial Storage</h4>
        <p>Persist to GeoPackage, PostGIS, and SpatiaLite with auto table creation</p>
    </td>
    <td align="center">
        <h4>Spider Framework</h4>
        <p>Scrapy-like API with concurrent crawling, pause/resume, and streaming</p>
    </td>
    <td align="center">
        <h4>Anti-Bot Bypass</h4>
        <p>Stealth mode with TLS fingerprinting and Cloudflare Turnstile bypass</p>
    </td>
</tr>
<tr>
    <td align="center">
        <h4>Adaptive Parsing</h4>
        <p>Smart element tracking that survives website layout changes</p>
    </td>
    <td align="center">
        <h4>AI Integration</h4>
        <p>Built-in MCP server for AI-assisted scraping with Claude and Cursor</p>
    </td>
    <td align="center">
        <h4>Geo CLI</h4>
        <p>10 commands for coord extraction, CRS lookup, conversion, and map preview</p>
    </td>
    <td align="center">
        <h4>High Performance</h4>
        <p>Optimized parsing engine outperforming most Python scraping libraries</p>
    </td>
</tr>
</table>

---

## Geospatial Intelligence

The geo module is what sets this fork apart. For the full API reference, see [docs/GEO_README.md](docs/GEO_README.md).

### Coordinate Extraction
Parse coordinates from free text, HTML pages, KML, GeoJSON, and GML in DD, DMS, DDM, UTM, MGRS, and Geohash formats.

```python
from scrapling.geo import CoordinateExtractor

extractor = CoordinateExtractor()
points = extractor.extract_from_text("""
    Summit: 27°59'17"N 86°55'31"E (8848m)
    Base camp: 28.0025, 86.8528
""")
for pt in points:
    print(f"{pt.y:.4f}, {pt.x:.4f} — {pt.quality.method}")
```

### CRS Engine
Transform between 9,000+ EPSG coordinate reference systems with automatic UTM zone detection, datum shifts, and geoid height queries.

```python
from scrapling.geo import CRSManager

crs = CRSManager()
coords = crs.transform([(583960, 4507523)], from_crs="EPSG:32618", to_crs="EPSG:4326")
utm_coords, utm_epsg = crs.to_utm([(-74.006, 40.7128)])
geoid_h = crs.get_geoid_height(40.7128, -74.006)
```

### OGC Services
Unified client for WFS, WMS, WCS, WMTS, and CSW geospatial web services.

```python
from scrapling.geo import OGCFetcher

wfs = OGCFetcher("https://example.com/wfs", service_type="WFS")
gdf = wfs.get_features("parcels", bbox=(10, 50, 11, 51), max_features=1000)
```

### Multi-Format Export
Export to GeoJSON, Shapefile, KML, KMZ, GML, GeoPackage, GeoTIFF, and CSV.

```python
from scrapling.geo import GeoExporter, GeoFeature
from shapely.geometry import Point

features = [
    GeoFeature(geometry=Point(31.2357, 30.0444), properties={"name": "Cairo"}),
    GeoFeature(geometry=Point(36.8219, -1.2921), properties={"name": "Nairobi"}),
]
GeoExporter().export(features, "cities.geojson")
GeoExporter().export(features, "cities.shp")
```

### GeoSpider Pipeline
Scrape-to-spatial pipeline that extracts, transforms, validates, and exports geospatial data in one pass.

```python
from scrapling.geo import GeoSpider
from scrapling.spiders import Response

class SurveySpider(GeoSpider):
    name = "survey"
    start_urls = ["https://data.example.com/stations"]
    default_crs = "EPSG:4326"
    output_crs = "EPSG:32637"
    output_format = "geojson"
    output_path = "stations.geojson"

    async def parse(self, response: Response):
        for pt in self.extract_coordinates(response):
            yield self.create_feature(
                geometry=pt.to_shapely(),
                properties={"source": response.url},
            )

SurveySpider().start()
```

### Spatial Storage
Persist features to GeoPackage, PostGIS, and SpatiaLite with automatic table creation.

```python
from scrapling.geo import GeoPackageStorage

gpkg = GeoPackageStorage("survey.gpkg")
gpkg.store(features, layer="control_points")
```

### Geo CLI
10 commands under `scrapling geo` for coordinate extraction, CRS lookup, format conversion, OGC queries, elevation, and map preview.

```bash
scrapling geo features https://example.com/wfs parcels -o parcels.geojson -n 5000
scrapling geo convert parcels.geojson parcels.shp --crs EPSG:32637
scrapling geo extract-coords https://example.com/locations
scrapling geo elevation 30.0444 31.2357
scrapling geo preview parcels.shp
```

> [!IMPORTANT]
> For the complete geospatial API — all classes, data models, validators, architecture, and testing — see **[docs/GEO_README.md](docs/GEO_README.md)**.

---

## Web Scraping

<details>
<summary><strong>Basic HTTP Requests</strong></summary>

```python
from scrapling.fetchers import Fetcher, FetcherSession

with FetcherSession(impersonate='chrome') as session:
    page = session.get('https://quotes.toscrape.com/', stealthy_headers=True)
    quotes = page.css('.quote .text::text').getall()

# Or use one-off requests
page = Fetcher.get('https://quotes.toscrape.com/')
quotes = page.css('.quote .text::text').getall()
```

</details>

<details>
<summary><strong>Stealth Mode</strong></summary>

```python
from scrapling.fetchers import StealthyFetcher, StealthySession

with StealthySession(headless=True, solve_cloudflare=True) as session:
    page = session.fetch('https://nopecha.com/demo/cloudflare', google_search=False)
    data = page.css('#padded_content a').getall()

# Or use one-off request style
page = StealthyFetcher.fetch('https://nopecha.com/demo/cloudflare')
data = page.css('#padded_content a').getall()
```

</details>

<details>
<summary><strong>Full Browser Automation</strong></summary>

```python
from scrapling.fetchers import DynamicFetcher, DynamicSession

with DynamicSession(headless=True, disable_resources=False, network_idle=True) as session:
    page = session.fetch('https://quotes.toscrape.com/', load_dom=False)
    data = page.xpath('//span[@class="text"]/text()').getall()

# Or use one-off request style
page = DynamicFetcher.fetch('https://quotes.toscrape.com/')
data = page.css('.quote .text::text').getall()
```

</details>

<details>
<summary><strong>Spider Framework</strong></summary>

Build full crawlers with concurrent requests, multiple session types, and pause/resume:

```python
from scrapling.spiders import Spider, Request, Response

class QuotesSpider(Spider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com/"]
    concurrent_requests = 10

    async def parse(self, response: Response):
        for quote in response.css('.quote'):
            yield {
                "text": quote.css('.text::text').get(),
                "author": quote.css('.author::text').get(),
            }

        next_page = response.css('.next a')
        if next_page:
            yield response.follow(next_page[0].attrib['href'])

result = QuotesSpider().start()
print(f"Scraped {len(result.items)} quotes")
result.items.to_json("quotes.json")
```

</details>

<details>
<summary><strong>Advanced Parsing & Navigation</strong></summary>

```python
from scrapling.fetchers import Fetcher

page = Fetcher.get('https://quotes.toscrape.com/')

# Multiple selection methods
quotes = page.css('.quote')                          # CSS selector
quotes = page.xpath('//div[@class="quote"]')         # XPath
quotes = page.find_all('div', {'class': 'quote'})   # BeautifulSoup-style
quotes = page.find_by_text('quote', tag='div')       # Text search

# Navigation
first_quote = page.css('.quote')[0]
author = first_quote.next_sibling.css('.author::text')
parent_container = first_quote.parent
similar_elements = first_quote.find_similar()
```

</details>

---

<details>
<summary><strong>Performance Benchmarks</strong></summary>

### Text Extraction Speed Test (5000 nested elements)

| # |      Library      | Time (ms) | vs Scrapling |
|---|:-----------------:|:---------:|:------------:|
| 1 |     Scrapling     |   2.02    |     1.0x     |
| 2 |   Parsel/Scrapy   |   2.04    |     1.01     |
| 3 |     Raw Lxml      |   2.54    |    1.257     |
| 4 |      PyQuery      |   24.17   |     ~12x     |
| 5 |    Selectolax     |   82.63   |     ~41x     |
| 6 |  MechanicalSoup   |  1549.71  |   ~767.1x    |
| 7 |   BS4 with Lxml   |  1584.31  |   ~784.3x    |
| 8 | BS4 with html5lib |  3391.91  |   ~1679.1x   |

> All benchmarks represent averages of 100+ runs. See [benchmarks.py](benchmarks.py) for methodology.

</details>

---

## Installation

```bash
pip install scrapling[geo]
```

> [!NOTE]
> This installs the full GeoScrapling toolkit: the Scrapling parsing engine, all fetchers, and the complete geospatial module (`pyproj`, `shapely`, `geopandas`, `fiona`, `rasterio`, `owslib`, and more). Run `scrapling install` after to set up browser dependencies.

<details>
<summary><strong>All Installation Options</strong></summary>

| Extra | Command | What You Get |
|---|---|---|
| **Base** | `pip install scrapling` | Parser engine only |
| **Fetchers** | `pip install "scrapling[fetchers]"` | HTTP + browser fetchers |
| **AI** | `pip install "scrapling[ai]"` | MCP server for Claude/Cursor |
| **Shell** | `pip install "scrapling[shell]"` | Interactive shell & `extract` command |
| **Geo** | `pip install "scrapling[geo]"` | Full geospatial module |
| **All** | `pip install "scrapling[all]"` | Everything above |

After installing any extra, run `scrapling install` to set up browser dependencies.

**Docker** — pre-built image with all extras and browsers:
```bash
docker pull ghcr.io/osman-geomatics93/geoscrapling:latest
```

</details>

---

## CLI & Interactive Shell

Launch the interactive web scraping shell:
```bash
scrapling shell
```
Extract pages directly from the terminal:
```bash
scrapling extract get 'https://example.com' content.md
scrapling extract get 'https://example.com' content.txt --css-selector '#main' --impersonate 'chrome'
scrapling extract stealthy-fetch 'https://nopecha.com/demo/cloudflare' captchas.html --solve-cloudflare
```

> [!NOTE]
> There are many additional features including the MCP server and the interactive shell. Check out the full documentation [here](https://scrapling.readthedocs.io/en/latest/).

---

## Contributing

We welcome contributions! Please read our [Contributing Guidelines](https://github.com/Osman-Geomatics93/GeoScrapling/blob/main/CONTRIBUTING.md) and [Code of Conduct](https://github.com/Osman-Geomatics93/GeoScrapling/blob/main/CODE_OF_CONDUCT.md) before getting started.

---

> [!CAUTION]
> **Disclaimer** — This library is provided for educational and research purposes only. By using this library, you agree to comply with local and international data scraping and privacy laws. The authors and contributors are not responsible for any misuse of this software. Always respect the terms of service of websites and robots.txt files.

---

## License

This work is licensed under the [BSD-3-Clause License](https://github.com/Osman-Geomatics93/GeoScrapling/blob/main/LICENSE).

## Acknowledgments

This project includes code adapted from:
- [Scrapling](https://github.com/D4Vinci/Scrapling) by Karim Shoair — the original web scraping framework this fork is built on
- [Parsel](https://github.com/scrapy/parsel) (BSD License) — Used for the [translator](https://github.com/Osman-Geomatics93/GeoScrapling/blob/main/scrapling/core/translator.py) submodule

---

<div align="center">
    <sub>Built on <a href="https://github.com/D4Vinci/Scrapling">Scrapling</a> by Karim Shoair &middot; Geospatial extension by <a href="https://github.com/Osman-Geomatics93">Osman-Geomatics93</a></sub>
</div>

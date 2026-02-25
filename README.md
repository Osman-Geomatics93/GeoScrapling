<h1 align="center">
    GeoScrapling
    <br>
    <small>Geospatial Intelligence meets Web Scraping</small>
</h1>

<p align="center">
    <a href="https://github.com/Osman-Geomatics93/GeoScrapling/actions/workflows/tests.yml">
        <img alt="Tests" src="https://github.com/Osman-Geomatics93/GeoScrapling/actions/workflows/tests.yml/badge.svg"></a>
    <a href="https://github.com/Osman-Geomatics93/GeoScrapling/blob/main/LICENSE">
        <img alt="License" src="https://img.shields.io/github/license/Osman-Geomatics93/GeoScrapling"></a>
    <a href="https://pypi.org/project/scrapling/">
        <img alt="Python versions" src="https://img.shields.io/pypi/pyversions/scrapling.svg"></a>
</p>

<p align="center">
    <a href="#geospatial-intelligence-geoscrapling"><strong>Geospatial</strong></a>
    &middot;
    <a href="https://scrapling.readthedocs.io/en/latest/parsing/selection/"><strong>Selection</strong></a>
    &middot;
    <a href="https://scrapling.readthedocs.io/en/latest/fetching/choosing/"><strong>Fetchers</strong></a>
    &middot;
    <a href="https://scrapling.readthedocs.io/en/latest/spiders/architecture.html"><strong>Spiders</strong></a>
    &middot;
    <a href="https://scrapling.readthedocs.io/en/latest/spiders/proxy-blocking.html"><strong>Proxy Rotation</strong></a>
    &middot;
    <a href="https://scrapling.readthedocs.io/en/latest/cli/overview/"><strong>CLI</strong></a>
    &middot;
    <a href="https://scrapling.readthedocs.io/en/latest/ai/mcp-server/"><strong>MCP</strong></a>
    &middot;
    <a href="docs/GEO_README.md"><strong>Geo Docs</strong></a>
</p>

**GeoScrapling** is a geospatial-enhanced fork of [Scrapling](https://github.com/D4Vinci/Scrapling) that combines a full-featured web scraping framework with professional-grade geospatial capabilities. It inherits all of Scrapling's strengths — adaptive parsing, anti-bot bypass, spider framework, MCP server — and adds coordinate extraction, CRS transformations, OGC web-service clients, multi-format spatial export, geo-aware spiders, and spatial storage for geomatics, geoinformatics, and surveying professionals.

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

## Geospatial Intelligence (GeoScrapling)

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

> For the complete geospatial API — all classes, data models, validators, architecture, and testing — see [docs/GEO_README.md](docs/GEO_README.md).

---

## Key Features

### Spiders — A Full Crawling Framework
- **Scrapy-like Spider API**: Define spiders with `start_urls`, async `parse` callbacks, and `Request`/`Response` objects.
- **Concurrent Crawling**: Configurable concurrency limits, per-domain throttling, and download delays.
- **Multi-Session Support**: Unified interface for HTTP requests and stealthy headless browsers in a single spider — route requests to different sessions by ID.
- **Pause & Resume**: Checkpoint-based crawl persistence. Press Ctrl+C for a graceful shutdown; restart to resume from where you left off.
- **Streaming Mode**: Stream scraped items as they arrive via `async for item in spider.stream()` with real-time stats.
- **Blocked Request Detection**: Automatic detection and retry of blocked requests with customizable logic.
- **Built-in Export**: Export results through hooks or the built-in JSON/JSONL with `result.items.to_json()` / `result.items.to_jsonl()`.

### Advanced Website Fetching with Session Support
- **HTTP Requests**: Fast and stealthy HTTP requests with the `Fetcher` class. Can impersonate browsers' TLS fingerprint, headers, and use HTTP/3.
- **Dynamic Loading**: Fetch dynamic websites with full browser automation through `DynamicFetcher` supporting Playwright's Chromium and Google's Chrome.
- **Anti-bot Bypass**: Advanced stealth capabilities with `StealthyFetcher` and fingerprint spoofing. Bypasses Cloudflare Turnstile/Interstitial with automation.
- **Session Management**: Persistent session support with `FetcherSession`, `StealthySession`, and `DynamicSession` for cookie and state management across requests.
- **Proxy Rotation**: Built-in `ProxyRotator` with cyclic or custom rotation strategies across all session types, plus per-request proxy overrides.
- **Domain Blocking**: Block requests to specific domains (and their subdomains) in browser-based fetchers.
- **Async Support**: Complete async support across all fetchers and dedicated async session classes.

### Adaptive Scraping & AI Integration
- **Smart Element Tracking**: Relocate elements after website changes using intelligent similarity algorithms.
- **Flexible Selection**: CSS selectors, XPath selectors, filter-based search, text search, regex search, and more.
- **Find Similar Elements**: Automatically locate elements similar to found elements.
- **MCP Server for AI**: Built-in MCP server for AI-assisted web scraping and data extraction with Claude, Cursor, and other AI tools.

### High-Performance Architecture
- **Lightning Fast**: Optimized performance outperforming most Python scraping libraries.
- **Memory Efficient**: Optimized data structures and lazy loading for a minimal memory footprint.
- **Fast JSON Serialization**: 10x faster than the standard library.
- **Battle Tested**: 92% test coverage and full type hints coverage.

### Developer-Friendly Experience
- **Interactive Shell**: Built-in IPython shell with Scrapling integration and tools like curl-to-Scrapling conversion.
- **CLI Usage**: Use Scrapling to scrape from the terminal without writing code.
- **Rich Navigation API**: Advanced DOM traversal with parent, sibling, and child navigation methods.
- **Enhanced Text Processing**: Built-in regex, cleaning methods, and optimized string operations.
- **Auto Selector Generation**: Generate robust CSS/XPath selectors for any element.
- **Familiar API**: Similar to Scrapy/BeautifulSoup with the same pseudo-elements used in Scrapy/Parsel.
- **Complete Type Coverage**: Full type hints for excellent IDE support. Scanned with PyRight and MyPy.
- **Docker Image**: Pre-built image with all browsers, automatically built with each release.

## Getting Started

### Basic Usage
HTTP requests with session support
```python
from scrapling.fetchers import Fetcher, FetcherSession

with FetcherSession(impersonate='chrome') as session:
    page = session.get('https://quotes.toscrape.com/', stealthy_headers=True)
    quotes = page.css('.quote .text::text').getall()

# Or use one-off requests
page = Fetcher.get('https://quotes.toscrape.com/')
quotes = page.css('.quote .text::text').getall()
```
Advanced stealth mode
```python
from scrapling.fetchers import StealthyFetcher, StealthySession

with StealthySession(headless=True, solve_cloudflare=True) as session:
    page = session.fetch('https://nopecha.com/demo/cloudflare', google_search=False)
    data = page.css('#padded_content a').getall()

# Or use one-off request style
page = StealthyFetcher.fetch('https://nopecha.com/demo/cloudflare')
data = page.css('#padded_content a').getall()
```
Full browser automation
```python
from scrapling.fetchers import DynamicFetcher, DynamicSession

with DynamicSession(headless=True, disable_resources=False, network_idle=True) as session:
    page = session.fetch('https://quotes.toscrape.com/', load_dom=False)
    data = page.xpath('//span[@class="text"]/text()').getall()

# Or use one-off request style
page = DynamicFetcher.fetch('https://quotes.toscrape.com/')
data = page.css('.quote .text::text').getall()
```

### Spiders
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

### Advanced Parsing & Navigation
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

## Performance Benchmarks

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

## Installation

Scrapling requires Python 3.10 or higher:

```bash
pip install scrapling
```

This installs only the parser engine. Add extras for additional features:

### Optional Dependencies

1. Install fetchers and browser dependencies:
    ```bash
    pip install "scrapling[fetchers]"
    scrapling install
    ```

2. Extra features:
   - MCP server: `pip install "scrapling[ai]"`
   - Interactive shell & `extract` command: `pip install "scrapling[shell]"`
   - Geospatial features: `pip install "scrapling[geo]"`
   - Everything: `pip install "scrapling[all]"`

   Remember to run `scrapling install` after any of these extras to install browser dependencies (if you haven't already).

### Docker
Pull a pre-built image with all extras and browsers:
```bash
docker pull ghcr.io/osman-geomatics93/geoscrapling:latest
```

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

## Contributing

We welcome contributions! Please read our [contributing guidelines](https://github.com/Osman-Geomatics93/GeoScrapling/blob/main/CONTRIBUTING.md) before getting started.

## Disclaimer

> [!CAUTION]
> This library is provided for educational and research purposes only. By using this library, you agree to comply with local and international data scraping and privacy laws. The authors and contributors are not responsible for any misuse of this software. Always respect the terms of service of websites and robots.txt files.

## License

This work is licensed under the BSD-3-Clause License.

## Acknowledgments

This project includes code adapted from:
- [Scrapling](https://github.com/D4Vinci/Scrapling) by Karim Shoair — the original web scraping framework this fork is built on
- Parsel (BSD License) — Used for the [translator](https://github.com/Osman-Geomatics93/GeoScrapling/blob/main/scrapling/core/translator.py) submodule

---
<div align="center">
    <small>Built on <a href="https://github.com/D4Vinci/Scrapling">Scrapling</a> by Karim Shoair &middot; Geospatial extension by <a href="https://github.com/Osman-Geomatics93">Osman-Geomatics93</a></small>
</div>

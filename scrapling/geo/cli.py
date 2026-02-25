"""CLI extensions for GeoScrapling geo commands.

Provides subcommands under ``scrapling geo ...`` for OGC service discovery,
format conversion, CRS transformation, geometry validation, coordinate
extraction, elevation queries, and map preview.
"""

from __future__ import annotations

try:
    from click import group, argument, option, echo
except (ImportError, ModuleNotFoundError) as e:
    raise ModuleNotFoundError(
        "The 'click' package is required for CLI commands. Install scrapling with the [fetchers] extra."
    ) from e


@group(help="Geospatial commands for GeoScrapling.")
def geo():
    """Geospatial subcommand group."""
    pass


# ── scrapling geo capabilities ──────────────────────────────────────────────


@geo.command(help="Probe OGC service capabilities.")
@argument("url")
def capabilities(url: str):
    """Fetch and display GetCapabilities from an OGC service."""
    from scrapling.geo.fetchers.ogc import OGCFetcher

    fetcher = OGCFetcher(url)
    caps = fetcher.get_capabilities()
    echo(f"Service type : {caps.get('type', 'unknown')}")
    echo(f"URL          : {caps.get('url', url)}")
    layers = caps.get("layers", [])
    echo(f"Layers ({len(layers)}):")
    for layer in layers:
        if isinstance(layer, dict):
            echo(f"  - {layer.get('name', '')}  ({layer.get('title', '')})")
        else:
            echo(f"  - {layer}")


# ── scrapling geo features ──────────────────────────────────────────────────


@geo.command(help="Download WFS features.")
@argument("wfs_url")
@argument("layer")
@option("--output", "-o", default="features.geojson", help="Output file path")
@option("--max-features", "-n", type=int, default=1000, help="Max features to fetch")
def features(wfs_url: str, layer: str, output: str, max_features: int):
    """Download features from a WFS layer and export."""
    from scrapling.geo.fetchers.ogc import OGCFetcher
    from scrapling.geo.exporters.base import GeoExporter
    from scrapling.geo.models import GeoFeature

    fetcher = OGCFetcher(wfs_url, service_type="WFS")
    gdf = fetcher.get_features(layer, max_features=max_features)
    echo(f"Fetched {len(gdf)} features from {layer}")

    geo_features = [
        GeoFeature(geometry=row.geometry, properties={c: row[c] for c in gdf.columns if c != "geometry"})
        for _, row in gdf.iterrows()
    ]
    GeoExporter().export(geo_features, output)
    echo(f"Exported to {output}")


# ── scrapling geo convert ───────────────────────────────────────────────────


@geo.command(help="Convert between geospatial formats.")
@argument("input_path")
@argument("output_path")
@option("--crs", default=None, help="Target CRS (e.g. EPSG:4326)")
def convert(input_path: str, output_path: str, crs: str | None):
    """Convert geospatial files between formats."""
    import geopandas as gpd
    from scrapling.geo.exporters.base import GeoExporter
    from scrapling.geo.models import GeoFeature

    gdf = gpd.read_file(input_path)
    if crs:
        gdf = gdf.to_crs(crs)

    feats = [
        GeoFeature(
            geometry=row.geometry,
            properties={c: row[c] for c in gdf.columns if c != "geometry"},
            crs=str(gdf.crs) if gdf.crs else "EPSG:4326",
        )
        for _, row in gdf.iterrows()
    ]
    GeoExporter(crs=crs or "EPSG:4326").export(feats, output_path)
    echo(f"Converted {input_path} -> {output_path} ({len(feats)} features)")


# ── scrapling geo transform ─────────────────────────────────────────────────


@geo.command(help="Transform a geospatial file to a different CRS.")
@argument("file_path")
@argument("target_crs")
@option("--output", "-o", default=None, help="Output path (overwrites input if omitted)")
def transform(file_path: str, target_crs: str, output: str | None):
    """Reproject a geospatial file."""
    import geopandas as gpd

    gdf = gpd.read_file(file_path)
    original_crs = str(gdf.crs)
    gdf = gdf.to_crs(target_crs)
    out = output or file_path
    gdf.to_file(out)
    echo(f"Transformed {file_path} from {original_crs} to {target_crs}")


# ── scrapling geo validate ──────────────────────────────────────────────────


@geo.command(help="Validate geometries in a geospatial file.")
@argument("file_path")
def validate(file_path: str):
    """Validate all geometries in a file and report issues."""
    import geopandas as gpd
    from scrapling.geo.validators.geometry import GeometryValidator

    gdf = gpd.read_file(file_path)
    validator = GeometryValidator()
    invalid_count = 0

    for idx, row in gdf.iterrows():
        valid, errors = validator.validate(row.geometry)
        if not valid:
            invalid_count += 1
            echo(f"  Feature {idx}: {'; '.join(errors)}")

    total = len(gdf)
    echo(f"\n{total - invalid_count}/{total} geometries valid")
    if invalid_count:
        echo(f"{invalid_count} invalid geometries found")


# ── scrapling geo extract-coords ────────────────────────────────────────────


@geo.command("extract-coords", help="Extract coordinates from a webpage.")
@argument("url")
def extract_coords(url: str):
    """Fetch a URL and extract geographic coordinates."""
    from scrapling.fetchers import Fetcher
    from scrapling.parser import Selector
    from scrapling.geo.parsers.coordinate import CoordinateExtractor

    resp = Fetcher.get(url)
    sel = Selector(resp.text)
    extractor = CoordinateExtractor()
    points = extractor.extract_from_html(sel)
    echo(f"Found {len(points)} coordinate(s):")
    for pt in points:
        echo(f"  {pt}")


# ── scrapling geo elevation ─────────────────────────────────────────────────


@geo.command(help="Query elevation at a point.")
@argument("lat", type=float)
@argument("lon", type=float)
def elevation(lat: float, lon: float):
    """Get elevation at (lat, lon)."""
    from scrapling.geo.fetchers.elevation import ElevationFetcher

    elev = ElevationFetcher().get_elevation(lat, lon)
    echo(f"Elevation at ({lat}, {lon}): {elev:.1f} m")


# ── scrapling geo preview ──────────────────────────────────────────────────


@geo.command(help="Open a map preview in the browser.")
@argument("file_path")
def preview(file_path: str):
    """Generate a Folium map from a geospatial file and open it."""
    import geopandas as gpd
    import folium
    import webbrowser
    import tempfile
    from pathlib import Path

    gdf = gpd.read_file(file_path)
    gdf = gdf.to_crs("EPSG:4326")

    centroid = gdf.dissolve().centroid.iloc[0]
    m = folium.Map(location=[centroid.y, centroid.x], zoom_start=10)
    folium.GeoJson(gdf.__geo_interface__).add_to(m)

    tmp = Path(tempfile.gettempdir()) / "geoscrapling_preview.html"
    m.save(str(tmp))
    webbrowser.open(str(tmp))
    echo(f"Preview opened: {tmp}")


# ── scrapling geo search ────────────────────────────────────────────────────


@geo.command(help="Search a CSW geospatial catalog.")
@argument("csw_url")
@argument("keyword")
@option("--max-records", "-n", type=int, default=20, help="Max records to return")
def search(csw_url: str, keyword: str, max_records: int):
    """Search an OGC CSW catalog by keyword."""
    from scrapling.geo.fetchers.ogc import OGCFetcher

    fetcher = OGCFetcher(csw_url, service_type="CSW")
    records = fetcher.search_catalog(keywords=[keyword], max_records=max_records)
    echo(f"Found {len(records)} record(s):")
    for rec in records:
        echo(f"  - {rec.get('title', rec.get('id', 'N/A'))}")
        if rec.get("abstract"):
            echo(f"    {rec['abstract'][:120]}...")


# ── scrapling geo tiles ─────────────────────────────────────────────────────


@geo.command(help="Download map tiles from a WMTS service.")
@argument("wmts_url")
@argument("bbox")  # "min_x,min_y,max_x,max_y"
@option("--layer", "-l", default=None, help="Layer name (auto-detect if omitted)")
@option("--zoom", "-z", type=int, default=12, help="Zoom level")
@option("--output-dir", "-o", default="tiles", help="Output directory")
def tiles(wmts_url: str, bbox: str, layer: str | None, zoom: int, output_dir: str):
    """Download tiles for a bounding box."""
    from pathlib import Path
    from scrapling.geo.fetchers.ogc import OGCFetcher

    coords = tuple(float(v) for v in bbox.split(","))
    if len(coords) != 4:
        echo("Error: bbox must be min_x,min_y,max_x,max_y")
        return

    fetcher = OGCFetcher(wmts_url, service_type="WMTS")
    if not layer:
        layers = fetcher.list_layers()
        if not layers:
            echo("No layers found")
            return
        layer = layers[0]
        echo(f"Using layer: {layer}")

    tile_data = fetcher.get_tiles_for_bbox(layer, coords, zoom)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for i, data in enumerate(tile_data):
        (out / f"tile_{i:04d}.png").write_bytes(data)

    echo(f"Downloaded {len(tile_data)} tiles to {out}/")

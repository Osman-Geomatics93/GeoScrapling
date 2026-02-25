"""GeoPackage exporter."""

from __future__ import annotations

from pathlib import Path

from scrapling.geo.models import GeoFeature


def geopackage_export(
    features: list[GeoFeature], path: str, crs: str = "EPSG:4326"
) -> Path:
    """Write features to an OGC GeoPackage file."""
    import geopandas as gpd

    if not features:
        raise ValueError("No features to export")

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    geoms = [f.geometry for f in features]
    props = [f.properties for f in features]
    gdf = gpd.GeoDataFrame(props, geometry=geoms, crs=crs)
    gdf.to_file(str(out), driver="GPKG")
    return out

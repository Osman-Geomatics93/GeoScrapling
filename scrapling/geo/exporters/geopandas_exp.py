"""GeoDataFrame bridge exporter."""

from __future__ import annotations

from scrapling.geo.models import GeoFeature


def to_geodataframe(features: list[GeoFeature], crs: str = "EPSG:4326"):
    """Convert GeoFeatures to a GeoDataFrame."""
    import geopandas as gpd

    if not features:
        return gpd.GeoDataFrame()

    geoms = [f.geometry for f in features]
    props = [f.properties for f in features]
    return gpd.GeoDataFrame(props, geometry=geoms, crs=crs)

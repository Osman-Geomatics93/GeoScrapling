"""ESRI Shapefile exporter."""

from __future__ import annotations

from pathlib import Path

from scrapling.geo.models import GeoFeature


def shapefile_export(features: list[GeoFeature], path: str, crs: str = "EPSG:4326") -> Path:
    """Write features to an ESRI Shapefile."""
    import fiona
    from fiona.crs import from_epsg
    from shapely.geometry import mapping

    if not features:
        raise ValueError("No features to export")

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Infer schema from the first feature
    first = features[0]
    geom_type = first.geometry.geom_type
    properties_schema: dict[str, str] = {}
    for key, val in first.properties.items():
        if isinstance(val, int):
            properties_schema[key] = "int"
        elif isinstance(val, float):
            properties_schema[key] = "float"
        else:
            properties_schema[key] = "str"

    schema = {"geometry": geom_type, "properties": properties_schema}

    epsg_code = int(crs.split(":")[1]) if ":" in crs else 4326
    with fiona.open(
        str(out),
        "w",
        driver="ESRI Shapefile",
        crs=from_epsg(epsg_code),
        schema=schema,
    ) as dst:
        for f in features:
            record = {
                "geometry": mapping(f.geometry),
                "properties": {k: v for k, v in f.properties.items() if k in properties_schema},
            }
            dst.write(record)

    return out

"""GeoJSON exporter."""

from __future__ import annotations

import json
from pathlib import Path

from scrapling.geo.models import GeoFeature


def geojson_export(features: list[GeoFeature], path: str) -> Path:
    """Write features to a GeoJSON file."""
    collection = {
        "type": "FeatureCollection",
        "features": [f.to_geojson() for f in features],
    }
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(collection, indent=2, default=str), encoding="utf-8")
    return out

"""KML / KMZ exporter."""

from __future__ import annotations

import zipfile
from pathlib import Path

from scrapling.geo.models import GeoFeature


def kml_export(features: list[GeoFeature], path: str) -> Path:
    """Write features to a KML file."""
    from fastkml import kml as fastkml_mod, geometry as fk_geometry
    from shapely.geometry import mapping

    k = fastkml_mod.KML()
    doc = fastkml_mod.Document(name="GeoScrapling Export")

    for feat in features:
        pm = fastkml_mod.Placemark(
            name=feat.properties.get("name", feat.id or ""),
            description=feat.properties.get("description", ""),
        )
        pm.geometry = feat.geometry
        doc.append(pm)

    k.append(doc)

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(k.to_string().decode("utf-8") if isinstance(k.to_string(), bytes) else k.to_string(),
                   encoding="utf-8")
    return out


def kmz_export(features: list[GeoFeature], path: str) -> Path:
    """Write features to a KMZ (compressed KML) file."""
    # Generate KML content first
    kml_path = Path(path).with_suffix(".kml")
    kml_export(features, str(kml_path))

    out = Path(path)
    with zipfile.ZipFile(str(out), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(str(kml_path), "doc.kml")
    kml_path.unlink(missing_ok=True)
    return out

"""KML / KMZ exporter."""

from __future__ import annotations

import zipfile
from pathlib import Path

from scrapling.geo.models import GeoFeature


def kml_export(features: list[GeoFeature], path: str) -> Path:
    """Write features to a KML file."""
    from fastkml import KML, Document, Placemark, create_kml_geometry

    k = KML()
    doc = Document(name="GeoScrapling Export")

    for feat in features:
        pm = Placemark(
            name=feat.properties.get("name", feat.id or ""),
            description=feat.properties.get("description", ""),
            kml_geometry=create_kml_geometry(feat.geometry),
        )
        doc.append(pm)

    k.append(doc)

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    kml_str = k.to_string()
    out.write_text(kml_str.decode("utf-8") if isinstance(kml_str, bytes) else kml_str, encoding="utf-8")
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

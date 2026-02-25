"""CSV exporter with coordinate columns and CRS metadata."""

from __future__ import annotations

import csv
from pathlib import Path

from scrapling.geo.models import GeoFeature


def csv_export(
    features: list[GeoFeature],
    path: str,
    coord_columns: tuple[str, str] = ("lon", "lat"),
) -> Path:
    """Write features to a CSV file with coordinate columns.

    The first line is a comment containing the CRS.
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not features:
        out.write_text("", encoding="utf-8")
        return out

    lon_col, lat_col = coord_columns

    # Collect all property keys
    all_keys: list[str] = []
    seen: set[str] = set()
    for f in features:
        for k in f.properties:
            if k not in seen:
                all_keys.append(k)
                seen.add(k)

    fieldnames = [lon_col, lat_col] + all_keys
    crs_info = features[0].crs if features else "EPSG:4326"

    with open(str(out), "w", newline="", encoding="utf-8") as fh:
        fh.write(f"# CRS: {crs_info}\n")
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for feat in features:
            centroid = feat.geometry.centroid
            row = {lon_col: centroid.x, lat_col: centroid.y}
            row.update(feat.properties)
            writer.writerow(row)

    return out

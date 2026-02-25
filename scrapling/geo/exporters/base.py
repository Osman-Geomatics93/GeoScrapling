"""Unified export interface for all geospatial formats."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scrapling.geo.models import GeoFeature


_FORMAT_MAP: dict[str, str] = {
    ".geojson": "geojson",
    ".json": "geojson",
    ".shp": "shapefile",
    ".kml": "kml",
    ".kmz": "kmz",
    ".gml": "gml",
    ".gpkg": "geopackage",
    ".tif": "geotiff",
    ".tiff": "geotiff",
    ".csv": "csv",
}


class GeoExporter:
    """Unified export interface for all geospatial formats.

    Delegates to format-specific exporters based on file extension or an
    explicit ``format`` argument.
    """

    def __init__(self, crs: str = "EPSG:4326"):
        self.crs = crs

    # ── Main entry point ────────────────────────────────────────────────

    def export(
        self,
        features: list[GeoFeature],
        path: str,
        format: str | None = None,
        crs: str | None = None,
    ) -> Path:
        """Export to any supported format (auto-detects from extension)."""
        out = Path(path)
        fmt = format or _FORMAT_MAP.get(out.suffix.lower(), "geojson")
        target_crs = crs or self.crs

        # Transform features if needed
        transformed = []
        for f in features:
            if f.crs != target_crs:
                transformed.append(f.transform(target_crs))
            else:
                transformed.append(f)

        dispatch = {
            "geojson": self.to_geojson,
            "shapefile": self.to_shapefile,
            "kml": self.to_kml,
            "kmz": self.to_kmz,
            "gml": self.to_gml,
            "geopackage": self.to_geopackage,
            "geotiff": self._geotiff_not_supported,
            "csv": self.to_csv,
        }

        if fmt not in dispatch:
            raise ValueError(f"Unsupported export format: {fmt!r}")
        return dispatch[fmt](transformed, str(out))

    # ── Format-specific exporters ───────────────────────────────────────

    def to_geojson(self, features: list[GeoFeature], path: str) -> Path:
        """Export features to GeoJSON."""
        from scrapling.geo.exporters.geojson_exp import geojson_export

        return geojson_export(features, path)

    def to_shapefile(self, features: list[GeoFeature], path: str) -> Path:
        """Export features to ESRI Shapefile."""
        from scrapling.geo.exporters.shapefile_exp import shapefile_export

        return shapefile_export(features, path, self.crs)

    def to_kml(self, features: list[GeoFeature], path: str) -> Path:
        """Export features to KML."""
        from scrapling.geo.exporters.kml_exp import kml_export

        return kml_export(features, path)

    def to_kmz(self, features: list[GeoFeature], path: str) -> Path:
        """Export features to KMZ (compressed KML)."""
        from scrapling.geo.exporters.kml_exp import kmz_export

        return kmz_export(features, path)

    def to_gml(self, features: list[GeoFeature], path: str) -> Path:
        """Export features to GML."""
        from scrapling.geo.exporters.gml_exp import gml_export

        return gml_export(features, path, self.crs)

    def to_geopackage(self, features: list[GeoFeature], path: str) -> Path:
        """Export features to OGC GeoPackage."""
        from scrapling.geo.exporters.geopackage_exp import geopackage_export

        return geopackage_export(features, path, self.crs)

    def to_geotiff(
        self,
        raster_data: Any,
        path: str,
        crs: str | None = None,
        transform: Any = None,
    ) -> Path:
        """Export raster data to GeoTIFF."""
        from scrapling.geo.exporters.geotiff_exp import geotiff_export

        return geotiff_export(raster_data, path, crs or self.crs, transform)

    def to_csv(
        self,
        features: list[GeoFeature],
        path: str,
        coord_columns: tuple[str, str] = ("lon", "lat"),
    ) -> Path:
        """Export features to CSV with coordinate columns."""
        from scrapling.geo.exporters.csv_exp import csv_export

        return csv_export(features, path, coord_columns)

    def to_geodataframe(self, features: list[GeoFeature]):
        """Convert features to a GeoDataFrame (no file output)."""
        from scrapling.geo.exporters.geopandas_exp import to_geodataframe

        return to_geodataframe(features, self.crs)

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _geotiff_not_supported(features: list[GeoFeature], path: str) -> Path:
        raise TypeError(
            "GeoTIFF export requires raster data, not vector features. "
            "Use GeoExporter.to_geotiff(raster_data, path, crs, transform) directly."
        )

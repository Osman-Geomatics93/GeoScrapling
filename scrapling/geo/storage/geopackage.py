"""GeoPackage (OGC standard) storage backend.

Uses ``geopandas`` + ``fiona`` for read/write and ``sqlite3`` for spatial
queries on the underlying SQLite database.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from scrapling.geo.models import GeoFeature, BoundingBox


class GeoPackageStorage:
    """GeoPackage (OGC standard) storage backend.

    Parameters
    ----------
    path : str
        Path to the ``.gpkg`` file.  Created automatically if it does not exist.
    default_crs : str
        Default CRS for new tables (default ``EPSG:4326``).
    """

    def __init__(self, path: str, default_crs: str = "EPSG:4326"):
        self.path = Path(path)
        self.default_crs = default_crs
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ── Write operations ────────────────────────────────────────────────

    def save_feature(self, table: str, feature: GeoFeature) -> None:
        """Save a single GeoFeature to a GeoPackage table."""
        self.save_features(table, [feature])

    def save_features(self, table: str, features: list[GeoFeature]) -> None:
        """Save multiple GeoFeatures to a GeoPackage table."""
        import geopandas as gpd

        if not features:
            return

        geoms = [f.geometry for f in features]
        props = [f.properties for f in features]
        crs = features[0].crs or self.default_crs
        gdf = gpd.GeoDataFrame(props, geometry=geoms, crs=crs)

        mode = "a" if self.path.exists() else "w"
        gdf.to_file(str(self.path), driver="GPKG", layer=table, mode=mode)

    # ── Read / query operations ─────────────────────────────────────────

    def query_bbox(
        self, table: str, bbox: tuple[float, float, float, float]
    ) -> list[GeoFeature]:
        """Query features within a bounding box."""
        import geopandas as gpd
        from shapely.geometry import box

        gdf = gpd.read_file(str(self.path), layer=table, bbox=bbox)
        return self._gdf_to_features(gdf)

    def query_within(self, table: str, geometry: Any) -> list[GeoFeature]:
        """Query features within a given geometry."""
        import geopandas as gpd

        gdf = gpd.read_file(str(self.path), layer=table)
        mask = gdf.within(geometry)
        return self._gdf_to_features(gdf[mask])

    def list_tables(self) -> list[str]:
        """List all layer / table names in the GeoPackage."""
        import fiona

        return fiona.listlayers(str(self.path))

    def get_table_crs(self, table: str) -> str:
        """Return the CRS string for a table."""
        import geopandas as gpd

        gdf = gpd.read_file(str(self.path), layer=table, rows=0)
        return str(gdf.crs) if gdf.crs else self.default_crs

    # ── Internal ────────────────────────────────────────────────────────

    @staticmethod
    def _gdf_to_features(gdf) -> list[GeoFeature]:
        features: list[GeoFeature] = []
        crs = str(gdf.crs) if gdf.crs else "EPSG:4326"
        for _, row in gdf.iterrows():
            props = {col: row[col] for col in gdf.columns if col != "geometry"}
            features.append(GeoFeature(geometry=row.geometry, properties=props, crs=crs))
        return features

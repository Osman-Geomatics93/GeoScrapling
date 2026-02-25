"""PostgreSQL / PostGIS storage backend for large-scale geospatial data.

Requires ``psycopg2`` (or ``psycopg2-binary``) and ``geopandas`` with
``sqlalchemy`` for seamless read/write.
"""

from __future__ import annotations

from typing import Any

from scrapling.geo.models import GeoFeature


class PostGISStorage:
    """PostgreSQL / PostGIS storage backend.

    Parameters
    ----------
    connection_string : str
        SQLAlchemy-compatible connection string, e.g.
        ``"postgresql://user:password@localhost:5432/geodb"``.
    schema : str
        Database schema to use (default ``"public"``).
    """

    def __init__(self, connection_string: str, schema: str = "public"):
        self.connection_string = connection_string
        self.schema = schema

    def _engine(self):
        from sqlalchemy import create_engine

        return create_engine(self.connection_string)

    # ── Write ───────────────────────────────────────────────────────────

    def save_feature(self, table: str, feature: GeoFeature) -> None:
        self.save_features(table, [feature])

    def save_features(self, table: str, features: list[GeoFeature]) -> None:
        """Bulk-insert features into a PostGIS table."""
        import geopandas as gpd

        if not features:
            return

        geoms = [f.geometry for f in features]
        props = [f.properties for f in features]
        crs = features[0].crs or "EPSG:4326"
        gdf = gpd.GeoDataFrame(props, geometry=geoms, crs=crs)
        gdf.to_postgis(
            table,
            self._engine(),
            schema=self.schema,
            if_exists="append",
            index=False,
        )

    # ── Read / query ────────────────────────────────────────────────────

    def query_bbox(
        self,
        table: str,
        bbox: tuple[float, float, float, float],
    ):
        """Query features within a bounding box. Returns a GeoDataFrame."""
        import geopandas as gpd

        min_x, min_y, max_x, max_y = bbox
        sql = (
            f"SELECT * FROM {self.schema}.{table} "
            f"WHERE geometry && ST_MakeEnvelope({min_x}, {min_y}, {max_x}, {max_y}, 4326)"
        )
        return gpd.read_postgis(sql, self._engine(), geom_col="geometry")

    def query_within(self, table: str, geometry: Any):
        """Query features within a given geometry. Returns a GeoDataFrame."""
        import geopandas as gpd
        from shapely import wkt

        wkt_str = geometry.wkt if hasattr(geometry, "wkt") else str(geometry)
        sql = (
            f"SELECT * FROM {self.schema}.{table} "
            f"WHERE ST_Within(geometry, ST_GeomFromText('{wkt_str}', 4326))"
        )
        return gpd.read_postgis(sql, self._engine(), geom_col="geometry")

    def query_nearest(
        self,
        table: str,
        point: Any,
        limit: int = 10,
    ):
        """Find nearest features to a point. Returns a GeoDataFrame."""
        import geopandas as gpd

        if hasattr(point, "x") and hasattr(point, "y"):
            x, y = point.x, point.y
        else:
            x, y = point[0], point[1]

        sql = (
            f"SELECT *, ST_Distance(geometry, ST_SetSRID(ST_Point({x}, {y}), 4326)) AS distance "
            f"FROM {self.schema}.{table} "
            f"ORDER BY geometry <-> ST_SetSRID(ST_Point({x}, {y}), 4326) "
            f"LIMIT {limit}"
        )
        return gpd.read_postgis(sql, self._engine(), geom_col="geometry")

    def spatial_join(
        self,
        table1: str,
        table2: str,
        predicate: str = "intersects",
    ):
        """Perform a spatial join between two PostGIS tables."""
        import geopandas as gpd

        predicate_map = {
            "intersects": "ST_Intersects",
            "within": "ST_Within",
            "contains": "ST_Contains",
            "overlaps": "ST_Overlaps",
            "touches": "ST_Touches",
        }
        st_func = predicate_map.get(predicate, "ST_Intersects")
        sql = (
            f"SELECT a.*, b.* FROM {self.schema}.{table1} a "
            f"JOIN {self.schema}.{table2} b "
            f"ON {st_func}(a.geometry, b.geometry)"
        )
        return gpd.read_postgis(sql, self._engine(), geom_col="geometry")

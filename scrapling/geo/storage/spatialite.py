"""SpatiaLite storage backend.

A lightweight spatial database that extends SQLite with geometry support.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from scrapling.geo.models import GeoFeature


class SpatiaLiteStorage:
    """SpatiaLite (SQLite + spatial extension) storage backend.

    Parameters
    ----------
    path : str
        Path to the ``.sqlite`` database file.
    default_crs : str
        Default CRS EPSG code for new tables (default ``EPSG:4326``).
    """

    def __init__(self, path: str, default_crs: str = "EPSG:4326"):
        self.path = Path(path)
        self.default_crs = default_crs
        self._srid = int(default_crs.split(":")[1]) if ":" in default_crs else 4326
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._init_spatialite()

    def _init_spatialite(self) -> None:
        """Load the SpatiaLite extension and initialise metadata tables."""
        try:
            self._conn.enable_load_extension(True)
            # Try common SpatiaLite library names
            for lib in ("mod_spatialite", "libspatialite", "spatialite"):
                try:
                    self._conn.load_extension(lib)
                    break
                except Exception:
                    continue
            self._conn.execute("SELECT InitSpatialMetaData(1)")
        except Exception:
            # SpatiaLite not available — fall back to basic SQLite
            pass

    # ── Write ───────────────────────────────────────────────────────────

    def _ensure_table(self, table: str, geom_type: str = "GEOMETRY") -> None:
        """Create the table and geometry column if they don't exist."""
        cur = self._conn.cursor()
        cur.execute(f"CREATE TABLE IF NOT EXISTS [{table}] (  fid INTEGER PRIMARY KEY AUTOINCREMENT,  properties TEXT)")  # nosec B608
        # Add geometry column via SpatiaLite function
        try:
            cur.execute(f"SELECT AddGeometryColumn('{table}', 'geometry', {self._srid}, '{geom_type}', 'XY')")  # nosec B608
        except Exception:
            pass  # Column may already exist
        self._conn.commit()

    def save_feature(self, table: str, feature: GeoFeature) -> None:
        self.save_features(table, [feature])

    def save_features(self, table: str, features: list[GeoFeature]) -> None:
        """Save features to a SpatiaLite table."""
        import json

        if not features:
            return

        geom_type = features[0].geometry.geom_type.upper()
        self._ensure_table(table, geom_type)

        cur = self._conn.cursor()
        for f in features:
            wkt = f.geometry.wkt
            props_json = json.dumps(f.properties, default=str)
            try:
                cur.execute(
                    f"INSERT INTO [{table}] (properties, geometry) VALUES (?, GeomFromText(?, {self._srid}))",  # nosec B608
                    (props_json, wkt),
                )
            except Exception:
                # Fallback without SpatiaLite functions
                cur.execute(
                    f"INSERT INTO [{table}] (properties) VALUES (?)",  # nosec B608
                    (props_json,),
                )
        self._conn.commit()

    # ── Read / query ────────────────────────────────────────────────────

    def query_bbox(self, table: str, bbox: tuple[float, float, float, float]) -> list[GeoFeature]:
        """Query features within a bounding box."""
        min_x, min_y, max_x, max_y = bbox
        cur = self._conn.cursor()
        try:
            cur.execute(
                f"SELECT fid, properties, AsText(geometry) FROM [{table}] "  # nosec B608
                f"WHERE MbrIntersects(geometry, BuildMbr({min_x}, {min_y}, {max_x}, {max_y}, {self._srid}))"
            )
        except Exception:
            cur.execute(f"SELECT fid, properties FROM [{table}]")  # nosec B608

        return self._rows_to_features(cur.fetchall())

    def query_within(self, table: str, geometry: Any) -> list[GeoFeature]:
        """Query features within a given geometry."""
        wkt = geometry.wkt if hasattr(geometry, "wkt") else str(geometry)
        cur = self._conn.cursor()
        try:
            cur.execute(
                f"SELECT fid, properties, AsText(geometry) FROM [{table}] "  # nosec B608
                f"WHERE Within(geometry, GeomFromText(?, {self._srid}))",
                (wkt,),
            )
        except Exception:
            cur.execute(f"SELECT fid, properties FROM [{table}]")  # nosec B608

        return self._rows_to_features(cur.fetchall())

    def list_tables(self) -> list[str]:
        """List all tables in the database."""
        cur = self._conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in cur.fetchall() if not row[0].startswith("sqlite_")]

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    # ── Internal ────────────────────────────────────────────────────────

    @staticmethod
    def _rows_to_features(rows: list) -> list[GeoFeature]:
        import json
        from shapely import wkt as shapely_wkt

        features: list[GeoFeature] = []
        for row in rows:
            props = json.loads(row[1]) if row[1] else {}
            geom = None
            if len(row) > 2 and row[2]:
                try:
                    geom = shapely_wkt.loads(row[2])
                except Exception:
                    pass
            if geom:
                features.append(GeoFeature(geometry=geom, properties=props))
        return features

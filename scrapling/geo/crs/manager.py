"""Central CRS transformation engine wrapping pyproj."""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any, Callable

from pyproj import CRS, Transformer
from pyproj.enums import TransformDirection

from scrapling.geo.crs.registry import CRSRegistry


class CRSManager:
    """Central CRS transformation engine wrapping pyproj.

    Provides coordinate transformations between any two coordinate reference
    systems, datum transformations, geoid height queries, and CRS detection.
    """

    def __init__(self, default_crs: str = "EPSG:4326"):
        self.default_crs = CRS.from_user_input(default_crs)
        self._registry = CRSRegistry()

    # ── Core transformations ────────────────────────────────────────────

    def transform(
        self,
        coords: list[tuple[float, float]],
        from_crs: str,
        to_crs: str,
    ) -> list[tuple[float, float]]:
        """Transform coordinates between any two CRS."""
        transformer = self._get_transformer(from_crs, to_crs)
        results: list[tuple[float, float]] = []
        for x, y in coords:
            tx, ty = transformer.transform(x, y)
            results.append((tx, ty))
        return results

    def to_wgs84(
        self, coords: list[tuple[float, float]], from_crs: str
    ) -> list[tuple[float, float]]:
        """Shortcut: transform to WGS84 (EPSG:4326)."""
        return self.transform(coords, from_crs, "EPSG:4326")

    def to_utm(
        self, coords: list[tuple[float, float]], from_crs: str | None = None
    ) -> tuple[list[tuple[float, float]], str]:
        """Auto-detect and transform to the appropriate UTM zone.

        Returns the transformed coordinates and the EPSG code of the UTM zone.
        """
        src_crs = from_crs or str(self.default_crs)
        # Convert first point to WGS84 for UTM zone detection
        if src_crs != "EPSG:4326":
            ref = self.to_wgs84([coords[0]], src_crs)[0]
        else:
            ref = coords[0]

        utm_code = self.get_utm_zone(ref[0], ref[1])
        transformed = self.transform(coords, src_crs, utm_code)
        return transformed, utm_code

    def to_local_grid(
        self,
        coords: list[tuple[float, float]],
        grid_name: str,
        from_crs: str | None = None,
    ) -> list[tuple[float, float]]:
        """Transform to a national / local grid system.

        ``grid_name`` can be an EPSG code or a well-known grid alias such as
        ``"OSGB36"`` (see :class:`CRSRegistry`).
        """
        src_crs = from_crs or str(self.default_crs)
        target = self._registry.resolve(grid_name)
        return self.transform(coords, src_crs, target)

    # ── Datum operations ────────────────────────────────────────────────

    def datum_transform(
        self,
        coords: list[tuple[float, float]],
        from_datum: str,
        to_datum: str,
    ) -> list[tuple[float, float]]:
        """Perform datum transformation with grid shifts."""
        return self.transform(coords, from_datum, to_datum)

    def get_geoid_height(
        self, lat: float, lon: float, geoid_model: str = "EGM2008"
    ) -> float:
        """Get geoid undulation at a point.

        Falls back to a simple approximation when the geoid grid is not
        installed locally.
        """
        try:
            geoid_crs = CRS.from_user_input(f"+proj=longlat +geoidgrids={geoid_model}")
            transformer = Transformer.from_crs(
                CRS.from_epsg(4326),
                geoid_crs,
                always_xy=True,
            )
            _, _, n = transformer.transform(lon, lat, 0)
            return float(n)
        except Exception:
            # Rough EGM96 approximation (for offline use)
            return -0.53 * math.cos(2 * math.radians(lat)) + 0.1

    def ellipsoidal_to_orthometric(
        self,
        lat: float,
        lon: float,
        h_ellipsoidal: float,
        geoid: str = "EGM2008",
    ) -> float:
        """Convert ellipsoidal height to orthometric height.

        orthometric = ellipsoidal - geoid_undulation
        """
        n = self.get_geoid_height(lat, lon, geoid)
        return h_ellipsoidal - n

    # ── Utilities ───────────────────────────────────────────────────────

    def detect_crs(self, wkt_or_proj: str) -> CRS:
        """Auto-detect CRS from WKT, PROJ string, or EPSG code."""
        return CRS.from_user_input(wkt_or_proj)

    def get_utm_zone(self, lon: float, lat: float) -> str:
        """Determine the appropriate UTM EPSG code from coordinates."""
        zone_number = int((lon + 180) / 6) + 1
        if lat >= 0:
            return f"EPSG:326{zone_number:02d}"
        return f"EPSG:327{zone_number:02d}"

    def crs_info(self, crs_code: str) -> dict[str, Any]:
        """Get full CRS metadata (name, area of use, accuracy)."""
        crs = CRS.from_user_input(crs_code)
        area = crs.area_of_use
        return {
            "name": crs.name,
            "authority": crs.to_authority(),
            "is_geographic": crs.is_geographic,
            "is_projected": crs.is_projected,
            "datum": crs.datum.name if crs.datum else None,
            "ellipsoid": crs.ellipsoid.name if crs.ellipsoid else None,
            "area_of_use": {
                "name": area.name if area else None,
                "bounds": (area.west, area.south, area.east, area.north) if area else None,
            },
            "units": str(crs.axis_info[0].unit_name) if crs.axis_info else None,
        }

    def get_transformer(self, from_crs: str, to_crs: str) -> Callable:
        """Return a callable suitable for ``shapely.ops.transform``."""
        transformer = self._get_transformer(from_crs, to_crs)

        def _transform(x, y, z=None):
            if z is not None:
                return transformer.transform(x, y, z)
            return transformer.transform(x, y)

        return _transform

    # ── Internal ────────────────────────────────────────────────────────

    @staticmethod
    @lru_cache(maxsize=64)
    def _get_transformer(from_crs: str, to_crs: str) -> Transformer:
        return Transformer.from_crs(
            CRS.from_user_input(from_crs),
            CRS.from_user_input(to_crs),
            always_xy=True,
        )

"""Fetch elevation / terrain data from DEM services.

Supports point elevation queries, batch queries, elevation profiles,
and DEM tile downloads.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


class ElevationFetcher:
    """Fetch elevation and terrain data from DEM services."""

    # Open Elevation API (free, open-source)
    _API_URL = "https://api.open-elevation.com/api/v1"

    def __init__(self, data_dir: str | Path = "elevation_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # ── Point queries ───────────────────────────────────────────────────

    def get_elevation(self, lat: float, lon: float) -> float:
        """Get elevation at a single point (metres above sea level)."""
        results = self.get_elevations([(lat, lon)])
        return results[0]

    def get_elevations(self, points: list[tuple[float, float]]) -> list[float]:
        """Batch elevation query for multiple (lat, lon) pairs."""
        import json
        import urllib.request

        locations = [{"latitude": lat, "longitude": lon} for lat, lon in points]
        body = json.dumps({"locations": locations}).encode("utf-8")
        req = urllib.request.Request(
            f"{self._API_URL}/lookup",
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:  # nosec B310
            data = json.loads(resp.read())

        return [r["elevation"] for r in data.get("results", [])]

    def get_elevation_profile(
        self,
        line,
        samples: int = 100,
    ) -> list[dict[str, float]]:
        """Get elevation profile along a Shapely LineString.

        Returns a list of ``{"distance": ..., "elevation": ..., "lat": ..., "lon": ...}``
        dicts, sampled at *samples* equidistant points along the line.
        """
        from shapely.geometry import LineString

        if not isinstance(line, LineString):
            raise TypeError("Expected a Shapely LineString")

        total_length = line.length
        distances = [total_length * i / (samples - 1) for i in range(samples)]
        pts = [line.interpolate(d) for d in distances]

        latlons = [(p.y, p.x) for p in pts]
        elevations = self.get_elevations(latlons)

        profile: list[dict[str, float]] = []
        for dist, (lat, lon), elev in zip(distances, latlons, elevations):
            profile.append(
                {
                    "distance": dist,
                    "elevation": elev,
                    "lat": lat,
                    "lon": lon,
                }
            )
        return profile

    # ── DEM tile downloads ──────────────────────────────────────────────

    def download_dem(
        self,
        bbox: tuple[float, float, float, float],
        resolution: str = "30m",
        source: str = "SRTM",
    ) -> Path:
        """Download DEM tiles for a bounding box.

        This is a simplified downloader that retrieves SRTM 30 m tiles from
        the AWS open data registry.

        Parameters
        ----------
        bbox : tuple
            (min_lon, min_lat, max_lon, max_lat).
        resolution : str
            ``"30m"`` or ``"90m"`` (SRTM GL1 / GL3).
        source : str
            Currently only ``"SRTM"`` is supported.
        """
        import math
        import urllib.request

        min_lon, min_lat, max_lon, max_lat = bbox

        # SRTM tiles are 1°×1°, named by SW corner
        lat_start = math.floor(min_lat)
        lat_end = math.floor(max_lat)
        lon_start = math.floor(min_lon)
        lon_end = math.floor(max_lon)

        downloaded: list[Path] = []
        for lat in range(lat_start, lat_end + 1):
            for lon in range(lon_start, lon_end + 1):
                ns = "N" if lat >= 0 else "S"
                ew = "E" if lon >= 0 else "W"
                tile_name = f"{ns}{abs(lat):02d}{ew}{abs(lon):03d}.hgt"
                url = f"https://elevation-tiles-prod.s3.amazonaws.com/skadi/{ns}{abs(lat):02d}/{tile_name}"
                dest = self.data_dir / tile_name
                if not dest.exists():
                    try:
                        urllib.request.urlretrieve(url, str(dest))  # nosec B310
                    except Exception:
                        continue
                downloaded.append(dest)

        if not downloaded:
            raise FileNotFoundError(f"No DEM tiles found for bbox {bbox}")
        return downloaded[0] if len(downloaded) == 1 else self.data_dir

    # ── Derived products ────────────────────────────────────────────────

    def get_slope(
        self,
        bbox: tuple[float, float, float, float],
        resolution: str = "30m",
    ) -> np.ndarray:
        """Compute slope (in degrees) for a bounding box."""
        dem_path = self.download_dem(bbox, resolution)
        return self._compute_terrain_attribute(dem_path, "slope")

    def get_aspect(
        self,
        bbox: tuple[float, float, float, float],
        resolution: str = "30m",
    ) -> np.ndarray:
        """Compute aspect (in degrees from north) for a bounding box."""
        dem_path = self.download_dem(bbox, resolution)
        return self._compute_terrain_attribute(dem_path, "aspect")

    @staticmethod
    def _compute_terrain_attribute(dem_path: Path, attribute: str) -> np.ndarray:
        """Compute slope or aspect from a DEM raster file."""
        import rasterio

        with rasterio.open(str(dem_path)) as src:
            elevation = src.read(1).astype(float)
            res = src.res[0]  # cell size in degrees

        # Convert cell size to approximate metres
        cell_m = res * 111_320  # rough conversion at equator

        dy, dx = np.gradient(elevation, cell_m)

        if attribute == "slope":
            return np.degrees(np.arctan(np.sqrt(dx**2 + dy**2)))
        elif attribute == "aspect":
            aspect = np.degrees(np.arctan2(-dx, dy))
            aspect[aspect < 0] += 360
            return aspect
        else:
            raise ValueError(f"Unknown attribute: {attribute}")

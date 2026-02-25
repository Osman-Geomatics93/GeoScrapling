"""Fetch satellite imagery metadata and data from major providers.

Supports Copernicus / Sentinel, Landsat (USGS), and generic STAC APIs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class SatelliteFetcher:
    """Fetch satellite imagery metadata and data from major providers."""

    def __init__(self, data_dir: str | Path = "satellite_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # ── Copernicus / Sentinel ───────────────────────────────────────────

    def search_sentinel(
        self,
        bbox: tuple[float, float, float, float],
        date_range: tuple[str, str],
        platform: str = "S2",
        cloud_cover_max: int = 20,
    ) -> list[dict[str, Any]]:
        """Search Copernicus Sentinel products via the STAC API.

        Parameters
        ----------
        bbox : tuple
            (min_lon, min_lat, max_lon, max_lat)
        date_range : tuple
            (start_date, end_date) as ISO-8601 strings (YYYY-MM-DD).
        platform : str
            ``"S1"`` for Sentinel-1, ``"S2"`` for Sentinel-2, etc.
        cloud_cover_max : int
            Maximum cloud cover percentage (Sentinel-2 only).
        """
        collection_map = {
            "S1": "sentinel-1-grd",
            "S2": "sentinel-2-l2a",
            "S3": "sentinel-3-olci-lfr",
            "S5P": "sentinel-5p-l2-no2",
        }
        collection = collection_map.get(platform.upper(), platform)
        return self.search_stac(
            stac_url="https://earth-search.aws.element84.com/v1",
            bbox=bbox,
            datetime=f"{date_range[0]}/{date_range[1]}",
            collections=[collection],
            query={"eo:cloud_cover": {"lte": cloud_cover_max}} if "2" in platform else None,
        )

    def download_sentinel_product(self, product_id: str, output_dir: str | Path | None = None) -> Path:
        """Download a Sentinel product by its STAC item ID.

        Requires network access to the Copernicus Data Space Ecosystem.
        """
        out = Path(output_dir) if output_dir else self.data_dir
        out.mkdir(parents=True, exist_ok=True)

        import urllib.request

        # Use the Copernicus STAC to get the download link
        stac_url = f"https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/{product_id}"
        import json

        with urllib.request.urlopen(stac_url, timeout=30) as resp:  # nosec B310
            item = json.loads(resp.read())

        # Download the thumbnail / first asset as an example
        assets = item.get("assets", {})
        for asset_key in ("visual", "thumbnail", "B04"):
            if asset_key in assets:
                href = assets[asset_key]["href"]
                dest = out / f"{product_id}_{asset_key}.tif"
                urllib.request.urlretrieve(href, str(dest))  # nosec B310
                return dest

        raise FileNotFoundError(f"No downloadable asset found for {product_id}")

    # ── Landsat (USGS) ─────────────────────────────────────────────────

    def search_landsat(
        self,
        bbox: tuple[float, float, float, float],
        date_range: tuple[str, str],
        collection: int = 2,
    ) -> list[dict[str, Any]]:
        """Search Landsat scenes via USGS STAC."""
        collection_name = f"landsat-c{collection}-l2"
        return self.search_stac(
            stac_url="https://landsatlook.usgs.gov/stac-server",
            bbox=bbox,
            datetime=f"{date_range[0]}/{date_range[1]}",
            collections=[collection_name],
        )

    # ── Generic STAC API support ────────────────────────────────────────

    def search_stac(
        self,
        stac_url: str,
        bbox: tuple[float, float, float, float] | None = None,
        datetime: str | None = None,
        collections: list[str] | None = None,
        query: dict | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Search a STAC API and return matching items."""
        import json
        import urllib.request

        search_url = f"{stac_url.rstrip('/')}/search"
        body: dict[str, Any] = {"limit": limit}
        if bbox:
            body["bbox"] = list(bbox)
        if datetime:
            body["datetime"] = datetime
        if collections:
            body["collections"] = collections
        if query:
            body["query"] = query

        req = urllib.request.Request(
            search_url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
            result = json.loads(resp.read())

        return result.get("features", [])

    # ── Metadata helpers ────────────────────────────────────────────────

    def get_scene_metadata(self, scene_id: str) -> dict[str, Any]:
        """Fetch full metadata for a scene from the STAC catalogue."""
        results = self.search_stac(
            stac_url="https://earth-search.aws.element84.com/v1",
            collections=["sentinel-2-l2a"],
            query={"id": {"eq": scene_id}} if scene_id else None,
            limit=1,
        )
        return results[0] if results else {}

    def get_thumbnail(self, scene_id: str) -> bytes:
        """Download a scene thumbnail image."""
        meta = self.get_scene_metadata(scene_id)
        thumb_url = meta.get("assets", {}).get("thumbnail", {}).get("href")
        if not thumb_url:
            raise FileNotFoundError(f"No thumbnail for scene {scene_id}")

        import urllib.request

        with urllib.request.urlopen(thumb_url, timeout=30) as resp:  # nosec B310
            return resp.read()

    def get_footprint(self, scene_id: str):
        """Get the spatial footprint of a scene as a Shapely Polygon."""
        from shapely.geometry import shape

        meta = self.get_scene_metadata(scene_id)
        geom = meta.get("geometry")
        if geom:
            return shape(geom)
        raise ValueError(f"No geometry found for scene {scene_id}")

"""SentinelSpider — spider for Copernicus Open Access Hub / STAC endpoints."""

from __future__ import annotations

from typing import Any

from scrapling.spiders.request import Request
from scrapling.geo.spiders.base import GeoSpider
from scrapling.geo.models import GeoFeature

from scrapling.core._types import Dict, Optional, AsyncGenerator, TYPE_CHECKING

if TYPE_CHECKING:
    from scrapling.engines.toolbelt.custom import Response


class SentinelSpider(GeoSpider):
    """Spider for discovering and cataloguing Sentinel satellite imagery.

    Uses the STAC API to search for Sentinel products and yields
    metadata items with footprint geometries.

    Attributes
    ----------
    search_bbox : tuple
        (min_lon, min_lat, max_lon, max_lat) area of interest.
    date_range : tuple[str, str]
        (start, end) dates as ISO strings ``YYYY-MM-DD``.
    platform : str
        Sentinel platform: ``"S1"``, ``"S2"``, ``"S3"``, ``"S5P"``.
    cloud_cover_max : int
        Maximum cloud cover percentage (Sentinel-2 only).
    download_thumbnails : bool
        If ``True``, download thumbnail images for each scene.
    """

    search_bbox: tuple = (-180, -90, 180, 90)
    date_range: tuple[str, str] = ("2024-01-01", "2024-12-31")
    platform: str = "S2"
    cloud_cover_max: int = 20
    download_thumbnails: bool = False

    async def start_requests(self) -> AsyncGenerator[Request, None]:
        # The actual search is done via the SatelliteFetcher, not HTTP requests.
        # We yield a dummy request to trigger parse().
        yield Request(
            "https://earth-search.aws.element84.com/v1",
            callback=self.parse,
            sid=self._session_manager.default_session_id,
        )

    async def parse(self, response: "Response") -> AsyncGenerator[Dict[str, Any] | Request | None, None]:
        """Search Sentinel imagery and yield scene metadata."""
        from scrapling.geo.fetchers.satellite import SatelliteFetcher
        from shapely.geometry import shape

        fetcher = SatelliteFetcher()
        results = fetcher.search_sentinel(
            bbox=self.search_bbox,
            date_range=self.date_range,
            platform=self.platform,
            cloud_cover_max=self.cloud_cover_max,
        )

        for item in results:
            geom = shape(item["geometry"]) if item.get("geometry") else None
            props = item.get("properties", {})
            props["id"] = item.get("id", "")
            props["stac_collection"] = item.get("collection", "")

            if geom:
                feature = self.create_feature(geom, props, feature_id=props.get("id"))
                yield {"_geo_feature": feature, **props}
            else:
                yield props

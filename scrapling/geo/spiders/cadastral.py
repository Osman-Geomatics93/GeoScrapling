"""CadastralSpider — spider for property / parcel scraping."""

from __future__ import annotations

from typing import Any

from scrapling.spiders.request import Request
from scrapling.geo.spiders.base import GeoSpider

from scrapling.core._types import Dict, Optional, AsyncGenerator, TYPE_CHECKING

if TYPE_CHECKING:
    from scrapling.engines.toolbelt.custom import Response


class CadastralSpider(GeoSpider):
    """Spider for scraping cadastral / land registry data.

    Wraps the :class:`CadastralFetcher` with the GeoSpider pipeline for
    automatic validation, CRS transformation, and export.

    Attributes
    ----------
    cadastral_wfs_url : str
        WFS endpoint serving cadastral parcels.
    parcel_layer : str
        Layer name for cadastral parcels.
    boundary_layer : str
        Layer name for cadastral boundaries.
    search_bbox : tuple or None
        Bounding box to restrict the search area.
    """

    cadastral_wfs_url: str = ""
    parcel_layer: str = "cp:CadastralParcel"
    boundary_layer: str = "cp:CadastralBoundary"
    search_bbox: Optional[tuple] = None

    async def start_requests(self) -> AsyncGenerator[Request, None]:
        if not self.cadastral_wfs_url:
            raise RuntimeError("cadastral_wfs_url must be set")
        cap_url = f"{self.cadastral_wfs_url}?service=WFS&request=GetCapabilities"
        yield Request(
            cap_url,
            callback=self.parse,
            sid=self._session_manager.default_session_id,
        )

    async def parse(
        self, response: "Response"
    ) -> AsyncGenerator[Dict[str, Any] | Request | None, None]:
        """Fetch cadastral parcels and boundaries."""
        from scrapling.geo.fetchers.cadastral import CadastralFetcher

        fetcher = CadastralFetcher(wfs_url=self.cadastral_wfs_url)

        # Parcels
        try:
            parcels_gdf = fetcher.search_parcels(
                bbox=self.search_bbox or self.bbox,
                layer=self.parcel_layer,
            )
            for _, row in parcels_gdf.iterrows():
                geom = row.geometry
                props = {col: row[col] for col in parcels_gdf.columns if col != "geometry"}
                props["feature_type"] = "parcel"
                feature = self.create_feature(geom, props)
                yield {"_geo_feature": feature, **props}
        except Exception as exc:
            self.logger.warning("Failed to fetch parcels: %s", exc)

        # Boundaries
        try:
            boundaries_gdf = fetcher.get_boundaries(
                bbox=self.search_bbox or self.bbox,
                layer=self.boundary_layer,
            )
            for _, row in boundaries_gdf.iterrows():
                geom = row.geometry
                props = {col: row[col] for col in boundaries_gdf.columns if col != "geometry"}
                props["feature_type"] = "boundary"
                feature = self.create_feature(geom, props)
                yield {"_geo_feature": feature, **props}
        except Exception as exc:
            self.logger.warning("Failed to fetch boundaries: %s", exc)

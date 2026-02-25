"""OGCSpider — spider for crawling OGC service catalogs and harvesting layers."""

from __future__ import annotations

from typing import Any

from scrapling.spiders.request import Request
from scrapling.geo.spiders.base import GeoSpider
from scrapling.geo.models import GeoFeature

from scrapling.core._types import Dict, Optional, AsyncGenerator, TYPE_CHECKING

if TYPE_CHECKING:
    from scrapling.engines.toolbelt.custom import Response


class OGCSpider(GeoSpider):
    """Spider for crawling OGC service catalogs and harvesting feature layers.

    Set ``service_urls`` and ``service_types`` before running.
    """

    service_urls: list[str] = []
    service_types: list[str] = ["WFS"]
    harvest_features: bool = True
    max_features_per_layer: int = 10_000

    async def start_requests(self) -> AsyncGenerator[Request, None]:
        """Auto-generate GetCapabilities requests for each service URL."""
        for url in self.service_urls:
            for stype in self.service_types:
                cap_url = f"{url}?service={stype}&request=GetCapabilities"
                yield Request(
                    cap_url,
                    callback=self.parse_capabilities,
                    meta={"service_url": url, "service_type": stype},
                    sid=self._session_manager.default_session_id,
                )

    async def parse(self, response: "Response") -> AsyncGenerator[Dict[str, Any] | Request | None, None]:
        """Default parse — delegates to parse_capabilities."""
        async for item in self.parse_capabilities(response):
            yield item

    async def parse_capabilities(self, response: "Response") -> AsyncGenerator[Dict[str, Any] | Request | None, None]:
        """Parse GetCapabilities and yield requests for each layer."""
        from scrapling.geo.parsers.ogc import OGCResponseParser

        parser = OGCResponseParser()
        if response.request is None:
            return
        stype = response.request.meta.get("service_type", "WFS")
        service_url = response.request.meta.get("service_url", self.service_urls[0] if self.service_urls else "")

        if stype == "WMS":
            caps = parser.parse_wms_capabilities(response.text)
            for layer in caps.get("layers", []):
                yield {
                    "type": "wms_layer",
                    "name": layer.get("name"),
                    "title": layer.get("title"),
                    "crs": layer.get("crs"),
                    "bbox": layer.get("bbox"),
                    "service_url": service_url,
                }
        elif stype == "WFS":
            # For WFS, we can also harvest the features
            caps_text = response.text
            try:
                caps = parser.parse_wms_capabilities(caps_text)
            except Exception:
                caps = {"layers": []}

            if self.harvest_features:
                from scrapling.geo.fetchers.ogc import OGCFetcher

                ogc = OGCFetcher(service_url, service_type="WFS")
                for layer_name in ogc.list_layers():
                    gdf = ogc.get_features(layer_name, max_features=self.max_features_per_layer)
                    for _, row in gdf.iterrows():
                        geom = row.geometry
                        props = {col: row[col] for col in gdf.columns if col != "geometry"}
                        feature = self.create_feature(geom, props)
                        yield {"_geo_feature": feature, **props}

        yield None  # End of generator

    async def parse_features(self, response: "Response") -> AsyncGenerator[Dict[str, Any] | Request | None, None]:
        """Parse WFS features into GeoFeatures."""
        from scrapling.geo.parsers.ogc import OGCResponseParser

        parser = OGCResponseParser()
        gdf = parser.parse_wfs_response(response.text)

        for _, row in gdf.iterrows():
            geom = row.geometry
            props = {col: row[col] for col in gdf.columns if col != "geometry"}
            feature = self.create_feature(geom, props)
            yield {"_geo_feature": feature, **props}

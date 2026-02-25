"""GeoportalSpider — spider for crawling national SDI / geoportal websites."""

from __future__ import annotations

from typing import Any

from scrapling.spiders.request import Request
from scrapling.geo.spiders.base import GeoSpider

from scrapling.core._types import Dict, Optional, AsyncGenerator, TYPE_CHECKING

if TYPE_CHECKING:
    from scrapling.engines.toolbelt.custom import Response


class GeoportalSpider(GeoSpider):
    """Spider for crawling national SDI (Spatial Data Infrastructure) geoportals.

    This spider discovers OGC service endpoints, metadata records, and
    downloadable datasets from geoportal catalogue pages.

    Attributes
    ----------
    portal_urls : list[str]
        Seed URLs for geoportal catalogue pages.
    follow_service_links : bool
        If ``True``, follow links to OGC service endpoints and fetch layers.
    download_datasets : bool
        If ``True``, download datasets linked from catalogue entries.
    """

    portal_urls: list[str] = []
    follow_service_links: bool = True
    download_datasets: bool = False

    async def start_requests(self) -> AsyncGenerator[Request, None]:
        for url in self.portal_urls or self.start_urls:
            yield Request(
                url,
                callback=self.parse,
                sid=self._session_manager.default_session_id,
            )

    async def parse(
        self, response: "Response"
    ) -> AsyncGenerator[Dict[str, Any] | Request | None, None]:
        """Parse a geoportal catalogue page."""
        from scrapling.parser import Selector

        sel = Selector(response.text)

        # Extract coordinates from the page
        coords = self.coord_extractor.extract_from_html(sel)
        for pt in coords:
            if self.within_bbox(pt):
                feature = self.create_feature(pt.to_shapely(), {"source_url": response.url})
                yield {"_geo_feature": feature, "source_url": response.url}

        # Discover OGC service links (WMS/WFS/WCS/WMTS)
        for link in sel.css("a[href]"):
            href = link.attrib.get("href", "")
            text = str(link.text()).lower() if link.text() else ""
            if any(svc in href.lower() for svc in ("wms", "wfs", "wcs", "wmts", "service=")):
                yield {
                    "type": "ogc_service_link",
                    "url": href,
                    "text": text,
                    "source_url": response.url,
                }
                if self.follow_service_links:
                    yield Request(
                        href,
                        callback=self.parse_service,
                        meta={"source_url": response.url},
                        sid=self._session_manager.default_session_id,
                    )

        # Follow pagination / catalogue links
        for link in sel.css("a.next, a[rel='next'], .pagination a"):
            href = link.attrib.get("href", "")
            if href:
                yield Request(
                    href,
                    callback=self.parse,
                    sid=self._session_manager.default_session_id,
                )

    async def parse_service(
        self, response: "Response"
    ) -> AsyncGenerator[Dict[str, Any] | Request | None, None]:
        """Parse an OGC service capabilities page."""
        from scrapling.geo.parsers.ogc import OGCResponseParser

        parser = OGCResponseParser()
        try:
            caps = parser.parse_wms_capabilities(response.text)
            for layer in caps.get("layers", []):
                yield {
                    "type": "ogc_layer",
                    "name": layer.get("name"),
                    "title": layer.get("title"),
                    "service_url": response.url,
                }
        except Exception:
            self.logger.debug("Could not parse capabilities from %s", response.url)
            yield None

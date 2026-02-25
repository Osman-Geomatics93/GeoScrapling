"""Unified client for OGC web services (WMS, WFS, WCS, WMTS, CSW).

Built on top of ``owslib`` with Scrapling fetcher integration for
undetectable HTTP requests when needed.
"""

from __future__ import annotations

from typing import Any

from scrapling.geo.models import BoundingBox, GeoFeature
from scrapling.geo.parsers.ogc import OGCResponseParser


class OGCFetcher:
    """Unified client for OGC web services.

    Parameters
    ----------
    base_url : str
        The base URL of the OGC service endpoint.
    service_type : str
        One of ``"WFS"``, ``"WMS"``, ``"WCS"``, ``"WMTS"``, ``"CSW"``, or
        ``"auto"`` (default) to auto-detect from GetCapabilities.
    fetcher : callable or None
        Optional Scrapling fetcher function for HTTP requests.  If ``None``
        the default ``owslib`` HTTP backend is used.
    """

    def __init__(
        self,
        base_url: str,
        service_type: str = "auto",
        fetcher: Any = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._fetcher = fetcher
        self._parser = OGCResponseParser()
        self._service_type = service_type.upper() if service_type != "auto" else None
        self._service: Any = None

    # ── Service bootstrapping ───────────────────────────────────────────

    def _ensure_service(self) -> None:
        """Lazy-connect to the service on first use."""
        if self._service is not None:
            return

        if self._service_type is None:
            self._service_type = self._detect_service_type()

        if self._service_type == "WFS":
            from owslib.wfs import WebFeatureService

            self._service = WebFeatureService(self.base_url, version="2.0.0")
        elif self._service_type == "WMS":
            from owslib.wms import WebMapService

            self._service = WebMapService(self.base_url, version="1.3.0")
        elif self._service_type == "WCS":
            from owslib.wcs import WebCoverageService

            self._service = WebCoverageService(self.base_url, version="2.0.1")
        elif self._service_type == "WMTS":
            from owslib.wmts import WebMapTileService

            self._service = WebMapTileService(self.base_url)
        elif self._service_type == "CSW":
            from owslib.csw import CatalogueServiceWeb

            self._service = CatalogueServiceWeb(self.base_url, version="2.0.2")
        else:
            raise ValueError(f"Unknown OGC service type: {self._service_type}")

    def _detect_service_type(self) -> str:
        """Probe the URL to determine the OGC service type."""
        import urllib.request
        import urllib.error

        for stype in ("WFS", "WMS", "WCS", "WMTS", "CSW"):
            probe_url = f"{self.base_url}?service={stype}&request=GetCapabilities"
            try:
                with urllib.request.urlopen(probe_url, timeout=15) as resp:  # nosec B310
                    data = resp.read(2048).decode("utf-8", errors="ignore")
                    if stype.lower() in data.lower():
                        return stype
            except (urllib.error.URLError, OSError):
                continue
        raise RuntimeError(f"Could not auto-detect OGC service type at {self.base_url}")

    # ── WFS — Web Feature Service ──────────────────────────────────────

    def get_features(
        self,
        layer: str,
        bbox: tuple | BoundingBox | None = None,
        crs: str | None = None,
        max_features: int | None = None,
        filter_expr: str | None = None,
    ):
        """Download vector features from a WFS layer.

        Returns a :class:`geopandas.GeoDataFrame`.
        """
        self._ensure_service()
        import io
        import geopandas as gpd

        kwargs: dict[str, Any] = {"typename": [layer], "outputFormat": "application/gml+xml; version=3.2"}
        if bbox is not None:
            if isinstance(bbox, BoundingBox):
                bbox = bbox.to_tuple()
            kwargs["bbox"] = bbox
        if crs:
            kwargs["srsname"] = crs
        if max_features:
            kwargs["maxfeatures"] = max_features

        resp = self._service.getfeature(**kwargs)
        data = resp.read() if hasattr(resp, "read") else resp
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        return self._parser.parse_wfs_response(data)

    # ── WMS — Web Map Service ──────────────────────────────────────────

    def get_map(
        self,
        layers: list[str],
        bbox: tuple,
        size: tuple[int, int],
        crs: str | None = None,
        format: str = "image/png",
        transparent: bool = True,
    ) -> bytes:
        """Request a rendered map image from WMS."""
        self._ensure_service()
        srs = crs or "EPSG:4326"
        resp = self._service.getmap(
            layers=layers,
            srs=srs,
            bbox=bbox,
            size=size,
            format=format,
            transparent=transparent,
        )
        return resp.read() if hasattr(resp, "read") else resp

    # ── WCS — Web Coverage Service ─────────────────────────────────────

    def get_coverage(
        self,
        coverage_id: str,
        bbox: tuple | None = None,
        crs: str | None = None,
        format: str = "GeoTIFF",
    ) -> bytes:
        """Download raster coverage data."""
        self._ensure_service()
        kwargs: dict[str, Any] = {"identifier": [coverage_id], "format": format}
        if bbox:
            kwargs["bbox"] = bbox
        if crs:
            kwargs["crs"] = crs
        resp = self._service.getCoverage(**kwargs)
        return resp.read() if hasattr(resp, "read") else resp

    # ── WMTS — Web Map Tile Service ────────────────────────────────────

    def get_tile(self, layer: str, zoom: int, row: int, col: int) -> bytes:
        """Fetch a single map tile."""
        self._ensure_service()
        resp = self._service.gettile(
            layer=layer,
            tilematrix=str(zoom),
            row=row,
            column=col,
            format="image/png",
        )
        return resp.read() if hasattr(resp, "read") else resp

    def get_tiles_for_bbox(self, layer: str, bbox: tuple, zoom: int) -> list[bytes]:
        """Fetch all tiles covering a bounding box at the given zoom."""
        import math

        min_x, min_y, max_x, max_y = bbox
        n = 2**zoom

        def _lon_to_col(lon: float) -> int:
            return int((lon + 180) / 360 * n)

        def _lat_to_row(lat: float) -> int:
            lat_r = math.radians(lat)
            return int((1 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * n)

        col_min, col_max = _lon_to_col(min_x), _lon_to_col(max_x)
        row_min, row_max = _lat_to_row(max_y), _lat_to_row(min_y)

        tiles: list[bytes] = []
        for r in range(row_min, row_max + 1):
            for c in range(col_min, col_max + 1):
                tiles.append(self.get_tile(layer, zoom, r, c))
        return tiles

    # ── CSW — Catalogue Service ────────────────────────────────────────

    def search_catalog(
        self,
        keywords: list[str] | None = None,
        bbox: tuple | None = None,
        time_range: tuple[str, str] | None = None,
        max_records: int = 100,
    ) -> list[dict[str, Any]]:
        """Search a CSW catalogue."""
        self._ensure_service()
        from owslib.fes import BBox, PropertyIsLike

        constraints = []
        if keywords:
            for kw in keywords:
                constraints.append(PropertyIsLike("csw:AnyText", f"%{kw}%"))
        if bbox:
            constraints.append(BBox(list(bbox)))

        self._service.getrecords2(
            constraints=constraints,
            maxrecords=max_records,
            esn="full",
        )

        records: list[dict[str, Any]] = []
        for _id, rec in self._service.records.items():
            records.append(
                {
                    "id": _id,
                    "title": rec.title,
                    "abstract": rec.abstract,
                    "type": rec.type,
                    "subjects": rec.subjects,
                    "bbox": getattr(rec, "bbox", None),
                    "references": getattr(rec, "references", []),
                }
            )
        return records

    # ── Discovery helpers ───────────────────────────────────────────────

    def get_capabilities(self) -> dict[str, Any]:
        """Return parsed GetCapabilities as a dict."""
        self._ensure_service()
        if self._service_type == "WMS":
            return self._parser.parse_wms_capabilities(
                self._service.getServiceXML().decode("utf-8", errors="replace")
                if hasattr(self._service, "getServiceXML")
                else ""
            )
        info: dict[str, Any] = {
            "type": self._service_type,
            "url": self.base_url,
            "layers": self.list_layers(),
        }
        return info

    def list_layers(self) -> list[str]:
        """List available layer / coverage / type names."""
        self._ensure_service()
        if hasattr(self._service, "contents"):
            return list(self._service.contents.keys())
        return []

    def get_layer_info(self, layer: str) -> dict[str, Any]:
        """Get metadata about a specific layer."""
        self._ensure_service()
        if hasattr(self._service, "contents") and layer in self._service.contents:
            obj = self._service.contents[layer]
            return {
                "name": layer,
                "title": getattr(obj, "title", ""),
                "abstract": getattr(obj, "abstract", ""),
                "crs": list(getattr(obj, "crsOptions", [])),
                "bbox": getattr(obj, "boundingBoxWGS84", None),
            }
        return {"name": layer}

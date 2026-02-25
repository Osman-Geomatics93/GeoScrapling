"""Fetch cadastral / land registry data.

Provides parcel search, geometry retrieval, and land-use queries.
Currently supports WFS-based cadastral services and can be extended with
country-specific backends.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from scrapling.geo.models import BoundingBox

if TYPE_CHECKING:
    from scrapling.geo.fetchers.ogc import OGCFetcher


class CadastralFetcher:
    """Fetch cadastral / land registry data.

    By default, the fetcher connects to the INSPIRE cadastral WFS service.
    You can override ``wfs_url`` to point to a different national cadastral
    endpoint.
    """

    # Default: INSPIRE Cadastral Parcels (example endpoint — replace per country)
    DEFAULT_WFS = ""

    def __init__(self, wfs_url: str | None = None):
        self.wfs_url = wfs_url or self.DEFAULT_WFS
        self._ogc: OGCFetcher | None = None

    def _get_ogc(self):
        if self._ogc is None and self.wfs_url:
            from scrapling.geo.fetchers.ogc import OGCFetcher

            self._ogc = OGCFetcher(self.wfs_url, service_type="WFS")
        return self._ogc

    # ── Parcel search ───────────────────────────────────────────────────

    def search_parcels(
        self,
        bbox: tuple | BoundingBox | None = None,
        address: str | None = None,
        owner: str | None = None,
        layer: str = "cp:CadastralParcel",
    ):
        """Search for cadastral parcels.

        Returns a :class:`geopandas.GeoDataFrame`.
        """
        ogc = self._get_ogc()
        if ogc is None:
            raise RuntimeError("No WFS URL configured for CadastralFetcher")

        return ogc.get_features(
            layer=layer,
            bbox=bbox.to_tuple() if isinstance(bbox, BoundingBox) else bbox,
        )

    def get_parcel_info(self, parcel_id: str, layer: str = "cp:CadastralParcel") -> dict[str, Any]:
        """Get metadata for a specific parcel."""
        ogc = self._get_ogc()
        if ogc is None:
            raise RuntimeError("No WFS URL configured for CadastralFetcher")

        gdf = ogc.get_features(
            layer=layer,
            filter_expr=f"nationalCadastralReference='{parcel_id}'",
            max_features=1,
        )
        if gdf.empty:
            return {}
        return gdf.iloc[0].to_dict()

    def get_parcel_geometry(self, parcel_id: str, layer: str = "cp:CadastralParcel"):
        """Get the geometry of a specific parcel as a Shapely Polygon."""
        info = self.get_parcel_info(parcel_id, layer)
        return info.get("geometry")

    def get_boundaries(
        self,
        bbox: tuple | BoundingBox | None = None,
        layer: str = "cp:CadastralBoundary",
    ):
        """Get cadastral boundaries within a bounding box.

        Returns a :class:`geopandas.GeoDataFrame`.
        """
        ogc = self._get_ogc()
        if ogc is None:
            raise RuntimeError("No WFS URL configured for CadastralFetcher")

        return ogc.get_features(
            layer=layer,
            bbox=bbox.to_tuple() if isinstance(bbox, BoundingBox) else bbox,
        )

    def get_land_use(
        self,
        bbox: tuple | BoundingBox | None = None,
        layer: str = "lu:LandUse",
    ):
        """Get land-use data within a bounding box.

        Returns a :class:`geopandas.GeoDataFrame`.
        """
        ogc = self._get_ogc()
        if ogc is None:
            raise RuntimeError("No WFS URL configured for CadastralFetcher")

        return ogc.get_features(
            layer=layer,
            bbox=bbox.to_tuple() if isinstance(bbox, BoundingBox) else bbox,
        )

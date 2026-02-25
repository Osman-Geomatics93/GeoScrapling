"""GeoSpider — base spider with a geospatial processing pipeline.

Extends Scrapling's :class:`Spider` with CRS transformation, coordinate
extraction, geometry validation, and automatic export on completion.
"""

from __future__ import annotations

from typing import Any

from scrapling.spiders.spider import Spider
from scrapling.spiders.request import Request
from scrapling.geo.models import GeoPoint, GeoFeature, BoundingBox
from scrapling.geo.crs.manager import CRSManager
from scrapling.geo.parsers.coordinate import CoordinateExtractor
from scrapling.geo.parsers.geometry import GeometryParser
from scrapling.geo.exporters.base import GeoExporter
from scrapling.geo.validators.geometry import GeometryValidator

from scrapling.core._types import Dict, Optional, TYPE_CHECKING, AsyncGenerator

if TYPE_CHECKING:
    from scrapling.engines.toolbelt.custom import Response


class GeoSpider(Spider):
    """Base spider with geospatial processing pipeline.

    Subclass this to build spiders that automatically handle CRS
    transformations, geometry validation, coordinate extraction, and
    multi-format export.

    Attributes
    ----------
    default_crs : str
        CRS of incoming data (default ``EPSG:4326``).
    output_crs : str or None
        If set, all output geometries are transformed to this CRS.
    output_format : str
        Default export format (``"geojson"``, ``"shapefile"``, etc.).
    output_path : str or None
        File path to auto-export when the spider finishes.
    validate_geometries : bool
        Run geometry validation on every scraped feature.
    bbox : tuple or BoundingBox or None
        Optional spatial filter — only features intersecting this box are kept.
    """

    default_crs: str = "EPSG:4326"
    output_crs: Optional[str] = None
    output_format: str = "geojson"
    output_path: Optional[str] = None
    validate_geometries: bool = True
    bbox: Optional[tuple | BoundingBox] = None

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        self.crs_manager = CRSManager(self.default_crs)
        self.coord_extractor = CoordinateExtractor(self.default_crs)
        self.geometry_parser = GeometryParser()
        self.exporter = GeoExporter(crs=self.output_crs or self.default_crs)
        self._geometry_validator = GeometryValidator()
        self._geo_features: list[GeoFeature] = []

        if isinstance(self.bbox, tuple):
            self.bbox = BoundingBox(*self.bbox)

    # ── Pipeline hooks ──────────────────────────────────────────────────

    async def on_scraped_item(self, item: Dict[str, Any]) -> Dict[str, Any] | None:
        """Auto-applies CRS transformation, validation, and enrichment."""
        # If the item contains a GeoFeature, process it
        feature = item.get("_geo_feature")
        if isinstance(feature, GeoFeature):
            feature = await self.on_geo_feature(feature)
            if feature is None:
                return None
            item["_geo_feature"] = feature
            self._geo_features.append(feature)

        return item

    async def on_geo_feature(self, feature: GeoFeature) -> GeoFeature | None:
        """Override to process each geospatial feature.

        The default implementation performs:
        1. Geometry validation (if enabled)
        2. CRS transformation (if ``output_crs`` is set)
        3. Bounding-box filtering (if ``bbox`` is set)

        Return ``None`` to drop the feature.
        """
        # Validate
        if self.validate_geometries:
            valid, errors = self._geometry_validator.validate(feature.geometry)
            if not valid:
                self.logger.warning("Invalid geometry (id=%s): %s", feature.id, errors)
                feature = GeoFeature(
                    geometry=self._geometry_validator.fix_topology(feature.geometry),
                    properties=feature.properties,
                    crs=feature.crs,
                    id=feature.id,
                    quality=feature.quality,
                )

        # Transform CRS
        if self.output_crs and feature.crs != self.output_crs:
            feature = feature.transform(self.output_crs)

        # Spatial filter
        if self.bbox is not None:
            bbox_obj = self.bbox if isinstance(self.bbox, BoundingBox) else BoundingBox(*self.bbox)
            if not bbox_obj.to_polygon().intersects(feature.geometry):
                return None

        return feature

    async def on_close(self) -> None:
        """Auto-export results in configured format on completion."""
        if self._geo_features and self.output_path:
            self.exporter.export(
                self._geo_features,
                self.output_path,
                format=self.output_format,
            )
            self.logger.info(
                "Exported %d features to %s", len(self._geo_features), self.output_path
            )
        await super().on_close()

    # ── Utility methods available in parse() ────────────────────────────

    def extract_coordinates(self, response: "Response") -> list[GeoPoint]:
        """Extract all coordinates from a response page."""
        from scrapling.parser import Selector

        sel = Selector(response.text)
        return self.coord_extractor.extract_from_html(sel)

    def transform_to_output_crs(self, geometry) -> Any:
        """Transform geometry to the spider's output CRS."""
        if self.output_crs:
            from shapely.ops import transform as shapely_transform

            transformer = self.crs_manager.get_transformer(self.default_crs, self.output_crs)
            return shapely_transform(transformer, geometry)
        return geometry

    def within_bbox(self, point: GeoPoint) -> bool:
        """Check if a point falls within the spider's bbox filter."""
        if self.bbox is None:
            return True
        bbox_obj = self.bbox if isinstance(self.bbox, BoundingBox) else BoundingBox(*self.bbox)
        return bbox_obj.contains(point)

    def create_feature(
        self,
        geometry: Any,
        properties: dict,
        feature_id: str | None = None,
    ) -> GeoFeature:
        """Create a GeoFeature with the spider's default CRS."""
        return GeoFeature(
            geometry=geometry,
            properties=properties,
            crs=self.default_crs,
            id=feature_id,
        )

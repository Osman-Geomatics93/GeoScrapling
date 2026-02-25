"""Parse responses from OGC web services (WFS, WMS, WCS, WMTS, CSW)."""

from __future__ import annotations

from typing import Any
from xml.etree import ElementTree as ET

from scrapling.geo.models import GeoFeature


# Common OGC XML namespaces
_NS = {
    "gml": "http://www.opengis.net/gml",
    "gml32": "http://www.opengis.net/gml/3.2",
    "wfs": "http://www.opengis.net/wfs",
    "wfs20": "http://www.opengis.net/wfs/2.0",
    "wms": "http://www.opengis.net/wms",
    "wcs": "http://www.opengis.net/wcs",
    "wcs20": "http://www.opengis.net/wcs/2.0",
    "wmts": "http://www.opengis.net/wmts/1.0",
    "ows": "http://www.opengis.net/ows/1.1",
    "csw": "http://www.opengis.net/cat/csw/2.0.2",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dct": "http://purl.org/dc/terms/",
    "ogc": "http://www.opengis.net/ogc",
    "xlink": "http://www.w3.org/1999/xlink",
    "iso19115": "http://www.isotc211.org/2005/gmd",
}


class OGCResponseParser:
    """Parse responses from OGC web services."""

    # ── WFS ─────────────────────────────────────────────────────────────

    def parse_wfs_response(self, xml_content: str):
        """Parse a WFS GetFeature response into a GeoDataFrame.

        Handles both WFS 1.x (GML 2/3) and WFS 2.0 (GML 3.2) responses.
        """
        import geopandas as gpd
        import io

        try:
            # fiona / geopandas can parse WFS GML natively
            gdf = gpd.read_file(io.BytesIO(xml_content.encode("utf-8")), driver="GML")
            return gdf
        except Exception:
            # Fall back to manual parsing
            features = self.parse_gml_features(xml_content)
            if not features:
                return gpd.GeoDataFrame()
            geoms = [f.geometry for f in features]
            props = [f.properties for f in features]
            return gpd.GeoDataFrame(props, geometry=geoms, crs="EPSG:4326")

    # ── WMS ─────────────────────────────────────────────────────────────

    def parse_wms_capabilities(self, xml_content: str) -> dict[str, Any]:
        """Parse a WMS GetCapabilities response."""
        root = ET.fromstring(xml_content)
        result: dict[str, Any] = {
            "version": root.attrib.get("version", ""),
            "title": "",
            "abstract": "",
            "layers": [],
        }

        # Try WMS 1.3.0 namespace and plain
        # Note: do NOT use `elem or elem` — Element truth value is deprecated
        service = root.find("Service")
        if service is None:
            service = root.find("{http://www.opengis.net/wms}Service")
        if service is not None:
            title = service.find("Title")
            if title is None:
                title = service.find("{http://www.opengis.net/wms}Title")
            abstract = service.find("Abstract")
            if abstract is None:
                abstract = service.find("{http://www.opengis.net/wms}Abstract")
            result["title"] = title.text if title is not None else ""
            result["abstract"] = abstract.text if abstract is not None else ""

        # Extract layers
        for layer_elem in root.iter("Layer"):
            name_el = layer_elem.find("Name")
            title_el = layer_elem.find("Title")
            if name_el is not None:
                layer_info: dict[str, Any] = {
                    "name": name_el.text or "",
                    "title": title_el.text if title_el is not None else "",
                    "queryable": layer_elem.attrib.get("queryable", "0") == "1",
                    "crs": [],
                }
                for crs_el in layer_elem.findall("CRS"):
                    if crs_el.text:
                        layer_info["crs"].append(crs_el.text)
                for srs_el in layer_elem.findall("SRS"):
                    if srs_el.text:
                        layer_info["crs"].append(srs_el.text)

                bbox_el = layer_elem.find("EX_GeographicBoundingBox")
                if bbox_el is None:
                    bbox_el = layer_elem.find("LatLonBoundingBox")
                if bbox_el is not None:
                    layer_info["bbox"] = self._parse_bbox_element(bbox_el)

                result["layers"].append(layer_info)

        return result

    # ── WCS ─────────────────────────────────────────────────────────────

    def parse_wcs_coverage(self, content: bytes):
        """Parse a WCS GetCoverage response into a rasterio dataset.

        The caller is responsible for closing the returned dataset.
        """
        import rasterio
        from io import BytesIO

        return rasterio.open(BytesIO(content))

    # ── WMTS ────────────────────────────────────────────────────────────

    def parse_wmts_capabilities(self, xml_content: str) -> dict[str, Any]:
        """Parse a WMTS GetCapabilities response."""
        root = ET.fromstring(xml_content)
        result: dict[str, Any] = {"layers": [], "tile_matrix_sets": []}

        for layer in root.iter("{http://www.opengis.net/wmts/1.0}Layer"):
            ows_id = layer.find("{http://www.opengis.net/ows/1.1}Identifier")
            ows_title = layer.find("{http://www.opengis.net/ows/1.1}Title")
            result["layers"].append({
                "identifier": ows_id.text if ows_id is not None else "",
                "title": ows_title.text if ows_title is not None else "",
            })

        for tms in root.iter("{http://www.opengis.net/wmts/1.0}TileMatrixSet"):
            ows_id = tms.find("{http://www.opengis.net/ows/1.1}Identifier")
            result["tile_matrix_sets"].append(
                ows_id.text if ows_id is not None else ""
            )

        return result

    # ── CSW ─────────────────────────────────────────────────────────────

    def parse_csw_records(self, xml_content: str) -> list[dict[str, Any]]:
        """Parse a CSW GetRecords response into a list of metadata dicts."""
        root = ET.fromstring(xml_content)
        records: list[dict[str, Any]] = []

        # Dublin Core records
        for rec in root.iter("{http://www.opengis.net/cat/csw/2.0.2}Record"):
            entry: dict[str, Any] = {}
            for child in rec:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                entry[tag] = child.text
            records.append(entry)

        # Brief / Summary records
        for tag_name in ("BriefRecord", "SummaryRecord"):
            for rec in root.iter(f"{{http://www.opengis.net/cat/csw/2.0.2}}{tag_name}"):
                entry = {}
                for child in rec:
                    tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    entry[tag] = child.text
                records.append(entry)

        return records

    # ── GML ─────────────────────────────────────────────────────────────

    def parse_gml_features(self, gml: str) -> list[GeoFeature]:
        """Parse GML feature members into GeoFeature objects."""
        from shapely.geometry import Point, LineString, Polygon

        root = ET.fromstring(gml)
        features: list[GeoFeature] = []

        # Iterate over featureMember / featureMembers
        for member in self._iter_feature_members(root):
            props: dict[str, Any] = {}
            geom = None

            for child in member:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

                # Try to find geometry children
                geom_candidate = self._parse_gml_geometry(child)
                if geom_candidate is not None:
                    geom = geom_candidate
                else:
                    props[tag] = child.text

            if geom is not None:
                features.append(GeoFeature(geometry=geom, properties=props, crs="EPSG:4326"))

        return features

    # ── Internal helpers ────────────────────────────────────────────────

    def _iter_feature_members(self, root: ET.Element):
        """Yield feature elements from GML featureMember / featureMembers."""
        for ns_prefix in ("gml", "gml32"):
            ns = _NS[ns_prefix]
            for fm in root.iter(f"{{{ns}}}featureMember"):
                for child in fm:
                    yield child
            for fms in root.iter(f"{{{ns}}}featureMembers"):
                for child in fms:
                    yield child

        # Also handle unnamespaced
        for fm in root.iter("featureMember"):
            for child in fm:
                yield child

    def _parse_gml_geometry(self, element: ET.Element):
        """Attempt to parse a GML geometry element into a Shapely object."""
        from shapely.geometry import Point, LineString, Polygon

        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

        # Check direct geometry type
        if tag == "Point":
            return self._parse_gml_point(element)
        if tag in ("LineString", "Curve"):
            return self._parse_gml_linestring(element)
        if tag in ("Polygon", "Surface"):
            return self._parse_gml_polygon(element)

        # Check children for geometry
        for child in element:
            result = self._parse_gml_geometry(child)
            if result is not None:
                return result

        return None

    def _parse_gml_point(self, elem: ET.Element):
        from shapely.geometry import Point

        coords = self._extract_gml_coords(elem)
        if coords and len(coords) >= 1:
            return Point(coords[0])
        return None

    def _parse_gml_linestring(self, elem: ET.Element):
        from shapely.geometry import LineString

        coords = self._extract_gml_coords(elem)
        if coords and len(coords) >= 2:
            return LineString(coords)
        return None

    def _parse_gml_polygon(self, elem: ET.Element):
        from shapely.geometry import Polygon

        # Look for exterior ring
        exterior = None
        interiors: list = []
        for child in elem.iter():
            child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if child_tag in ("exterior", "outerBoundaryIs"):
                coords = self._extract_gml_coords(child)
                if coords:
                    exterior = coords
            elif child_tag in ("interior", "innerBoundaryIs"):
                coords = self._extract_gml_coords(child)
                if coords:
                    interiors.append(coords)

        if exterior:
            return Polygon(exterior, interiors or None)
        return None

    def _extract_gml_coords(self, elem: ET.Element) -> list[tuple[float, ...]]:
        """Extract coordinate tuples from various GML coordinate encodings."""
        coords: list[tuple[float, ...]] = []

        # <gml:pos> or <gml:posList>
        for pos_tag in ("pos", "posList"):
            for ns in (_NS["gml"], _NS["gml32"], ""):
                full_tag = f"{{{ns}}}{pos_tag}" if ns else pos_tag
                for pos_el in elem.iter(full_tag):
                    if pos_el.text:
                        values = pos_el.text.strip().split()
                        floats = [float(v) for v in values]
                        dim = int(pos_el.attrib.get("srsDimension", "2"))
                        for i in range(0, len(floats), dim):
                            coords.append(tuple(floats[i : i + dim]))

        # <gml:coordinates> (GML 2)
        for ns in (_NS["gml"], ""):
            full_tag = f"{{{ns}}}coordinates" if ns else "coordinates"
            for coord_el in elem.iter(full_tag):
                if coord_el.text:
                    cs = coord_el.attrib.get("cs", ",")
                    ts = coord_el.attrib.get("ts", " ")
                    for group in coord_el.text.strip().split(ts):
                        parts = group.split(cs)
                        coords.append(tuple(float(p) for p in parts))

        return coords

    @staticmethod
    def _parse_bbox_element(elem: ET.Element) -> dict[str, float] | None:
        """Extract bbox from either EX_GeographicBoundingBox or LatLonBoundingBox."""
        if elem.tag == "LatLonBoundingBox":
            try:
                return {
                    "minx": float(elem.attrib.get("minx", 0)),
                    "miny": float(elem.attrib.get("miny", 0)),
                    "maxx": float(elem.attrib.get("maxx", 0)),
                    "maxy": float(elem.attrib.get("maxy", 0)),
                }
            except (ValueError, TypeError):
                return None

        result: dict[str, float] = {}
        for tag, key in [
            ("westBoundLongitude", "minx"),
            ("southBoundLatitude", "miny"),
            ("eastBoundLongitude", "maxx"),
            ("northBoundLatitude", "maxy"),
        ]:
            child = elem.find(tag)
            if child is not None and child.text:
                result[key] = float(child.text)
        return result if len(result) == 4 else None

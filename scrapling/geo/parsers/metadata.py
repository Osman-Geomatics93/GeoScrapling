"""Spatial metadata parser for ISO 19115 and Dublin Core records."""

from __future__ import annotations

from typing import Any
from xml.etree import ElementTree as ET


_NS = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
    "gmx": "http://www.isotc211.org/2005/gmx",
    "gml": "http://www.opengis.net/gml/3.2",
    "srv": "http://www.isotc211.org/2005/srv",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dct": "http://purl.org/dc/terms/",
}


class SpatialMetadataParser:
    """Parse spatial metadata from ISO 19115 and Dublin Core XML records."""

    def parse_iso19115(self, xml_content: str) -> dict[str, Any]:
        """Parse an ISO 19115 metadata XML document.

        Returns a flat dictionary with the most commonly used fields.
        """
        root = ET.fromstring(xml_content)
        meta: dict[str, Any] = {}

        meta["file_identifier"] = self._text(root, "gmd:fileIdentifier/gco:CharacterString")
        meta["language"] = self._text(root, "gmd:language/gco:CharacterString")
        meta["date_stamp"] = self._text(root, "gmd:dateStamp/gco:Date") or self._text(
            root, "gmd:dateStamp/gco:DateTime"
        )

        # Identification info
        ident = root.find(self._ns("gmd:identificationInfo/gmd:MD_DataIdentification"))
        if ident is not None:
            citation = ident.find(self._ns("gmd:citation/gmd:CI_Citation"))
            if citation is not None:
                meta["title"] = self._text(citation, "gmd:title/gco:CharacterString")
                meta["date"] = self._text(
                    citation, "gmd:date/gmd:CI_Date/gmd:date/gco:Date"
                )
            meta["abstract"] = self._text(ident, "gmd:abstract/gco:CharacterString")

            # Keywords
            keywords: list[str] = []
            for kw_el in ident.iter(self._ns_tag("gmd", "keyword")):
                cs = kw_el.find(self._ns_tag("gco", "CharacterString"))
                if cs is not None and cs.text:
                    keywords.append(cs.text)
            meta["keywords"] = keywords

            # Extent / bbox
            extent = ident.find(
                self._ns("gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox")
            )
            if extent is not None:
                meta["bbox"] = {
                    "west": self._float(extent, "gmd:westBoundLongitude/gco:Decimal"),
                    "east": self._float(extent, "gmd:eastBoundLongitude/gco:Decimal"),
                    "south": self._float(extent, "gmd:southBoundLatitude/gco:Decimal"),
                    "north": self._float(extent, "gmd:northBoundLatitude/gco:Decimal"),
                }

        # Reference system
        ref_sys = root.find(self._ns("gmd:referenceSystemInfo/gmd:MD_ReferenceSystem"))
        if ref_sys is not None:
            code = self._text(
                ref_sys,
                "gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:code/gco:CharacterString",
            )
            meta["crs"] = code

        return meta

    def parse_dublin_core(self, xml_content: str) -> dict[str, Any]:
        """Parse a Dublin Core metadata XML document."""
        root = ET.fromstring(xml_content)
        meta: dict[str, Any] = {}

        for ns_prefix in ("dc", "dct"):
            ns = _NS[ns_prefix]
            for child in root:
                if child.tag.startswith(f"{{{ns}}}"):
                    tag = child.tag.replace(f"{{{ns}}}", "")
                    if tag in meta:
                        if isinstance(meta[tag], list):
                            meta[tag].append(child.text)
                        else:
                            meta[tag] = [meta[tag], child.text]
                    else:
                        meta[tag] = child.text

        return meta

    # ── Internal helpers ────────────────────────────────────────────────

    def _ns(self, path: str) -> str:
        """Expand namespace prefixes in an XPath-like path."""
        parts = path.split("/")
        expanded: list[str] = []
        for part in parts:
            if ":" in part:
                prefix, local = part.split(":", 1)
                if prefix in _NS:
                    expanded.append(f"{{{_NS[prefix]}}}{local}")
                else:
                    expanded.append(part)
            else:
                expanded.append(part)
        return "/".join(expanded)

    @staticmethod
    def _ns_tag(prefix: str, local: str) -> str:
        return f"{{{_NS[prefix]}}}{local}"

    def _text(self, elem: ET.Element, path: str) -> str | None:
        child = elem.find(self._ns(path))
        if child is not None and child.text:
            return child.text.strip()
        return None

    def _float(self, elem: ET.Element, path: str) -> float | None:
        text = self._text(elem, path)
        if text:
            try:
                return float(text)
            except ValueError:
                pass
        return None

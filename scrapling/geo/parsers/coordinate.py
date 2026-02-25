"""Extract coordinates from text, HTML, and structured geospatial formats."""

from __future__ import annotations

import re
import math
from typing import Any

from scrapling.geo.models import GeoPoint, GeoFeature, CoordinateQuality

# ── Regex patterns ──────────────────────────────────────────────────────────

# Decimal degrees: 40.7128, -74.0060  or  40.7128° N, 74.0060° W
_DD_PAIR = re.compile(
    r"(?P<lat>[+-]?\d{1,3}\.\d{2,10})\s*°?\s*(?P<lat_h>[NSns])?"
    r"\s*[,;\s/]+\s*"
    r"(?P<lon>[+-]?\d{1,3}\.\d{2,10})\s*°?\s*(?P<lon_h>[EWew])?"
)

# DMS: 40°42'46"N 74°00'22"W
_DMS = re.compile(
    r"(?P<d>\d{1,3})\s*[°]\s*"
    r"(?P<m>\d{1,2})\s*[′']\s*"
    r"(?P<s>\d{1,2}(?:\.\d+)?)\s*[″\"]?\s*"
    r"(?P<h>[NSEWnsew])"
)

# DDM: 40°42.766'N
_DDM = re.compile(
    r"(?P<d>\d{1,3})\s*[°]\s*"
    r"(?P<m>\d{1,2}(?:\.\d+)?)\s*[′']\s*"
    r"(?P<h>[NSEWnsew])"
)

# UTM: 18T 583960 4507523
_UTM = re.compile(
    r"(?P<zone>\d{1,2})\s*(?P<letter>[C-Xc-x])\s+"
    r"(?P<easting>\d{5,7}(?:\.\d+)?)\s+"
    r"(?P<northing>\d{5,8}(?:\.\d+)?)"
)

# MGRS: 18TWL8396007523 (variable precision)
_MGRS = re.compile(r"(?P<mgrs>\d{1,2}[C-Xc-x][A-Za-z]{2}\d{4,10})")

# Geohash (base-32, 4-12 chars)
_GEOHASH = re.compile(r"\b(?P<gh>[0-9b-hjkmnp-z]{5,12})\b", re.IGNORECASE)


class CoordinateExtractor:
    """Extract coordinates from any text, HTML, or structured data."""

    def __init__(self, default_crs: str = "EPSG:4326"):
        self.default_crs = default_crs

    # ── Free text extraction ────────────────────────────────────────────

    def extract_from_text(self, text: str) -> list[GeoPoint]:
        """Find all coordinate patterns in free text."""
        points: list[GeoPoint] = []

        # DMS pairs — collect individual DMS matches, pair them lat/lon
        dms_matches = list(_DMS.finditer(text))
        used_dms: set[int] = set()
        for i in range(len(dms_matches) - 1):
            if i in used_dms:
                continue
            m1, m2 = dms_matches[i], dms_matches[i + 1]
            h1, h2 = m1.group("h").upper(), m2.group("h").upper()
            if h1 in "NS" and h2 in "EW":
                lat = self.parse_dms(m1.group())
                lon = self.parse_dms(m2.group())
                points.append(GeoPoint(x=lon, y=lat, crs=self.default_crs,
                                       quality=CoordinateQuality(source="text-dms", method="parsed")))
                used_dms.update({i, i + 1})

        # Decimal degree pairs
        for m in _DD_PAIR.finditer(text):
            lat = float(m.group("lat"))
            lon = float(m.group("lon"))
            if m.group("lat_h") and m.group("lat_h").upper() == "S":
                lat = -lat
            if m.group("lon_h") and m.group("lon_h").upper() == "W":
                lon = -lon
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                points.append(GeoPoint(x=lon, y=lat, crs=self.default_crs,
                                       quality=CoordinateQuality(source="text-dd", method="parsed")))

        # UTM
        for m in _UTM.finditer(text):
            try:
                lat, lon = self.parse_utm(m.group())
                points.append(GeoPoint(x=lon, y=lat, crs=self.default_crs,
                                       quality=CoordinateQuality(source="text-utm", method="parsed")))
            except Exception:
                pass

        return points

    def extract_from_html(self, selector: Any) -> list[GeoPoint]:
        """Extract coordinates from HTML meta tags, microdata, and embedded maps.

        ``selector`` should be a Scrapling :class:`Selector` instance.
        """
        points: list[GeoPoint] = []

        # <meta name="geo.position" content="lat;lon">
        geo_pos = selector.css('meta[name="geo.position"]::attr(content)').get()
        if geo_pos:
            parts = re.split(r"[;,]", geo_pos)
            if len(parts) == 2:
                try:
                    lat, lon = float(parts[0]), float(parts[1])
                    points.append(GeoPoint(x=lon, y=lat, crs="EPSG:4326",
                                           quality=CoordinateQuality(source="meta-geo.position")))
                except ValueError:
                    pass

        # <meta property="place:location:latitude"> / <meta property="place:location:longitude">
        og_lat = selector.css('meta[property="place:location:latitude"]::attr(content)').get()
        og_lon = selector.css('meta[property="place:location:longitude"]::attr(content)').get()
        if og_lat and og_lon:
            try:
                points.append(GeoPoint(
                    x=float(og_lon), y=float(og_lat), crs="EPSG:4326",
                    quality=CoordinateQuality(source="meta-og"),
                ))
            except ValueError:
                pass

        # Schema.org GeoCoordinates in JSON-LD
        for script in selector.css('script[type="application/ld+json"]::text').getall():
            points.extend(self._parse_jsonld_geo(script))

        # Fall back to free-text extraction on the body
        body_text = selector.css("body").text()
        if body_text:
            points.extend(self.extract_from_text(str(body_text)))

        return points

    def extract_from_table(self, selector: Any):
        """Parse HTML tables with coordinate columns and return a GeoDataFrame."""
        import geopandas as gpd
        import pandas as pd
        from shapely.geometry import Point

        headers: list[str] = []
        rows: list[list[str]] = []

        for th in selector.css("table th"):
            headers.append(th.text().strip().lower() if th.text() else "")
        for tr in selector.css("table tr"):
            cells = [td.text().strip() if td.text() else "" for td in tr.css("td")]
            if cells:
                rows.append(cells)

        if not headers or not rows:
            return gpd.GeoDataFrame()

        df = pd.DataFrame(rows, columns=headers[: len(rows[0])] if headers else None)

        # Auto-detect lat/lon columns
        lat_col = lon_col = None
        for col in df.columns:
            cl = str(col).lower()
            if cl in ("lat", "latitude", "y"):
                lat_col = col
            elif cl in ("lon", "lng", "longitude", "x"):
                lon_col = col

        if lat_col and lon_col:
            df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
            df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
            geometry = [
                Point(row[lon_col], row[lat_col])
                if pd.notna(row[lat_col]) and pd.notna(row[lon_col])
                else None
                for _, row in df.iterrows()
            ]
            return gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

        return gpd.GeoDataFrame(df)

    # ── Structured format extraction ────────────────────────────────────

    def extract_from_kml(self, content: str) -> list[GeoFeature]:
        """Extract features from KML content."""
        from fastkml import kml as fastkml_mod

        features: list[GeoFeature] = []
        k = fastkml_mod.KML()
        k.from_string(content)
        for doc in k.features():
            features.extend(self._walk_kml_features(doc))
        return features

    def extract_from_geojson(self, content: str) -> list[GeoFeature]:
        """Extract features from a GeoJSON string."""
        import json
        from shapely.geometry import shape

        data = json.loads(content) if isinstance(content, str) else content

        features: list[GeoFeature] = []
        if data.get("type") == "FeatureCollection":
            raw_features = data.get("features", [])
        elif data.get("type") == "Feature":
            raw_features = [data]
        else:
            # Bare geometry
            geom = shape(data)
            return [GeoFeature(geometry=geom, crs="EPSG:4326")]

        for f in raw_features:
            geom = shape(f["geometry"]) if f.get("geometry") else None
            props = f.get("properties", {})
            fid = f.get("id")
            if geom:
                features.append(GeoFeature(geometry=geom, properties=props, id=fid, crs="EPSG:4326"))
        return features

    def extract_from_gml(self, content: str) -> list[GeoFeature]:
        """Extract features from GML content."""
        from scrapling.geo.parsers.ogc import OGCResponseParser

        parser = OGCResponseParser()
        return parser.parse_gml_features(content)

    # ── Single-format parsers ───────────────────────────────────────────

    @staticmethod
    def parse_dms(dms_string: str) -> float:
        """Parse a DMS string like ``40°42'46\"N`` to decimal degrees."""
        m = _DMS.search(dms_string)
        if not m:
            # Try DDM
            m2 = _DDM.search(dms_string)
            if m2:
                d = float(m2.group("d"))
                minutes = float(m2.group("m"))
                dd = d + minutes / 60.0
                if m2.group("h").upper() in ("S", "W"):
                    dd = -dd
                return dd
            raise ValueError(f"Cannot parse DMS string: {dms_string!r}")

        d = float(m.group("d"))
        minutes = float(m.group("m"))
        s = float(m.group("s"))
        dd = d + minutes / 60.0 + s / 3600.0
        if m.group("h").upper() in ("S", "W"):
            dd = -dd
        return dd

    @staticmethod
    def parse_utm(utm_string: str) -> tuple[float, float]:
        """Parse a UTM string to (latitude, longitude) in WGS84."""
        m = _UTM.search(utm_string)
        if not m:
            raise ValueError(f"Cannot parse UTM string: {utm_string!r}")

        zone = int(m.group("zone"))
        letter = m.group("letter").upper()
        easting = float(m.group("easting"))
        northing = float(m.group("northing"))
        northern = letter >= "N"

        from scrapling.geo.crs.manager import CRSManager

        mgr = CRSManager()
        epsg = f"EPSG:326{zone:02d}" if northern else f"EPSG:327{zone:02d}"
        result = mgr.transform([(easting, northing)], epsg, "EPSG:4326")
        return result[0][1], result[0][0]  # lat, lon

    @staticmethod
    def parse_mgrs(mgrs_string: str) -> tuple[float, float]:
        """Parse an MGRS grid reference to (latitude, longitude).

        Requires the ``mgrs`` package.  Falls back to a basic zone-level
        approximation if the package is not available.
        """
        try:
            import mgrs as mgrs_lib

            m = mgrs_lib.MGRS()
            lat, lon = m.toLatLon(mgrs_string)
            return (lat, lon)
        except ImportError:
            raise ImportError(
                "The 'mgrs' package is required for MGRS parsing. "
                "Install it with: pip install mgrs"
            )

    # ── Internal helpers ────────────────────────────────────────────────

    def _parse_jsonld_geo(self, script_text: str) -> list[GeoPoint]:
        """Extract GeoCoordinates from a JSON-LD script block."""
        import json

        points: list[GeoPoint] = []
        try:
            data = json.loads(script_text)
        except (json.JSONDecodeError, ValueError):
            return points

        self._walk_jsonld(data, points)
        return points

    def _walk_jsonld(self, obj: Any, out: list[GeoPoint]) -> None:
        if isinstance(obj, dict):
            if obj.get("@type") == "GeoCoordinates":
                try:
                    lat = float(obj["latitude"])
                    lon = float(obj["longitude"])
                    out.append(GeoPoint(
                        x=lon, y=lat, crs="EPSG:4326",
                        quality=CoordinateQuality(source="json-ld"),
                    ))
                except (KeyError, ValueError, TypeError):
                    pass
            for v in obj.values():
                self._walk_jsonld(v, out)
        elif isinstance(obj, list):
            for item in obj:
                self._walk_jsonld(item, out)

    def _walk_kml_features(self, element: Any) -> list[GeoFeature]:
        """Recursively extract GeoFeatures from a KML element tree."""
        features: list[GeoFeature] = []
        if hasattr(element, "geometry") and element.geometry is not None:
            from shapely.geometry import shape

            geom = shape(element.geometry)
            props = {"name": getattr(element, "name", None),
                     "description": getattr(element, "description", None)}
            features.append(GeoFeature(geometry=geom, properties=props, crs="EPSG:4326"))
        if hasattr(element, "features"):
            for child in element.features():
                features.extend(self._walk_kml_features(child))
        return features

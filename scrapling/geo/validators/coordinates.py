"""Coordinate validation utilities."""

from __future__ import annotations


class CoordinateValidator:
    """Validate geographic and projected coordinates."""

    # WGS84 bounds
    _LAT_MIN, _LAT_MAX = -90.0, 90.0
    _LON_MIN, _LON_MAX = -180.0, 180.0

    def validate_lat_lon(
        self, lat: float, lon: float
    ) -> tuple[bool, list[str]]:
        """Validate WGS84 latitude/longitude pair."""
        errors: list[str] = []
        if not (self._LAT_MIN <= lat <= self._LAT_MAX):
            errors.append(f"Latitude {lat} out of range [{self._LAT_MIN}, {self._LAT_MAX}]")
        if not (self._LON_MIN <= lon <= self._LON_MAX):
            errors.append(f"Longitude {lon} out of range [{self._LON_MIN}, {self._LON_MAX}]")
        return (len(errors) == 0, errors)

    def validate_utm(
        self,
        easting: float,
        northing: float,
        zone: int,
    ) -> tuple[bool, list[str]]:
        """Validate UTM coordinates."""
        errors: list[str] = []
        if not (1 <= zone <= 60):
            errors.append(f"UTM zone {zone} out of range [1, 60]")
        if not (100_000 <= easting <= 900_000):
            errors.append(f"Easting {easting} out of typical range [100000, 900000]")
        if not (0 <= northing <= 10_000_000):
            errors.append(f"Northing {northing} out of range [0, 10000000]")
        return (len(errors) == 0, errors)

    def validate_precision(
        self, coord: float, min_decimals: int
    ) -> bool:
        """Check that a coordinate has at least *min_decimals* decimal places."""
        text = f"{coord:.15g}"
        if "." not in text:
            return min_decimals <= 0
        decimals = len(text.split(".")[1].rstrip("0"))
        return decimals >= min_decimals

    def check_on_land(self, lat: float, lon: float) -> bool:
        """Heuristic check whether a WGS84 point is likely on land.

        Uses a simplified bounding-box approach (not a full coastline test).
        Returns ``True`` when the point does *not* appear to be in open ocean.
        """
        # Very rough check: reject points in the middle of major oceans
        # This is a placeholder — a production implementation would use a
        # land-mask raster or a shapefile of land polygons.
        if lat < -60:  # Antarctica fringes / Southern Ocean
            return False
        # Atlantic gap (very rough)
        if -30 < lat < 30 and -40 < lon < -10:
            return False
        # Central Pacific
        if -20 < lat < 20 and 160 < lon <= 180:
            return False
        return True

    def check_in_country(
        self, lat: float, lon: float, country_code: str
    ) -> bool:
        """Check whether a coordinate falls within a country's bounding box.

        Uses approximate bounding boxes for a handful of common countries.
        Returns ``True`` when the point is within the bbox.
        """
        boxes: dict[str, tuple[float, float, float, float]] = {
            # (min_lon, min_lat, max_lon, max_lat)
            "US": (-125.0, 24.0, -66.0, 50.0),
            "GB": (-8.0, 49.9, 2.0, 61.0),
            "DE": (5.87, 47.27, 15.04, 55.06),
            "FR": (-5.14, 41.36, 9.56, 51.09),
            "AU": (113.0, -44.0, 154.0, -10.0),
            "CA": (-141.0, 41.7, -52.6, 83.1),
            "BR": (-73.99, -33.75, -34.79, 5.27),
            "IN": (68.18, 6.75, 97.4, 35.5),
            "CN": (73.5, 18.15, 134.77, 53.56),
            "JP": (129.5, 31.0, 145.8, 45.5),
        }
        code = country_code.upper()
        if code not in boxes:
            return True  # Unknown country — cannot reject
        min_lon, min_lat, max_lon, max_lat = boxes[code]
        return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat

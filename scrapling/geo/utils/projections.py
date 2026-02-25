"""Common projection helpers."""

from __future__ import annotations


def auto_utm_epsg(lon: float, lat: float) -> str:
    """Return the EPSG code for the UTM zone containing (lon, lat)."""
    zone = int((lon + 180) / 6) + 1
    if lat >= 0:
        return f"EPSG:326{zone:02d}"
    return f"EPSG:327{zone:02d}"


def lon_lat_to_web_mercator(lon: float, lat: float) -> tuple[float, float]:
    """Convert WGS84 lon/lat to Web Mercator (EPSG:3857) x/y."""
    import math

    x = lon * 20037508.34 / 180.0
    y = math.log(math.tan((90 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
    y = y * 20037508.34 / 180.0
    return (x, y)


def web_mercator_to_lon_lat(x: float, y: float) -> tuple[float, float]:
    """Convert Web Mercator (EPSG:3857) x/y to WGS84 lon/lat."""
    import math

    lon = x * 180.0 / 20037508.34
    lat = y * 180.0 / 20037508.34
    lat = 180.0 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180.0)) - math.pi / 2)
    return (lon, lat)


def is_geographic(crs_code: str) -> bool:
    """Check whether a CRS code refers to a geographic (degree-based) CRS."""
    from pyproj import CRS

    return CRS.from_user_input(crs_code).is_geographic


def is_projected(crs_code: str) -> bool:
    """Check whether a CRS code refers to a projected (metre-based) CRS."""
    from pyproj import CRS

    return CRS.from_user_input(crs_code).is_projected

"""Geo-aware fetchers for OGC, satellite, GNSS, elevation, and cadastral data."""

from scrapling.geo.fetchers.ogc import OGCFetcher
from scrapling.geo.fetchers.satellite import SatelliteFetcher
from scrapling.geo.fetchers.gnss import GNSSFetcher
from scrapling.geo.fetchers.elevation import ElevationFetcher
from scrapling.geo.fetchers.cadastral import CadastralFetcher

__all__ = [
    "OGCFetcher",
    "SatelliteFetcher",
    "GNSSFetcher",
    "ElevationFetcher",
    "CadastralFetcher",
]

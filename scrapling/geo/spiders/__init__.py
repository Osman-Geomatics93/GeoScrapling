"""Pre-built geospatial spiders."""

from scrapling.geo.spiders.base import GeoSpider
from scrapling.geo.spiders.ogc_spider import OGCSpider
from scrapling.geo.spiders.geoportal import GeoportalSpider
from scrapling.geo.spiders.sentinel import SentinelSpider
from scrapling.geo.spiders.cadastral import CadastralSpider

__all__ = [
    "GeoSpider",
    "OGCSpider",
    "GeoportalSpider",
    "SentinelSpider",
    "CadastralSpider",
]

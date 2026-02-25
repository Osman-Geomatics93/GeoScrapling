"""Common CRS definitions and aliases for quick lookup."""

from __future__ import annotations

from pyproj import CRS


# Well-known grid aliases → EPSG codes
_GRID_ALIASES: dict[str, str] = {
    # Geographic
    "WGS84": "EPSG:4326",
    "NAD83": "EPSG:4269",
    "NAD27": "EPSG:4267",
    "ETRS89": "EPSG:4258",
    # National grids
    "OSGB36": "EPSG:27700",
    "Irish Grid": "EPSG:29903",
    "Swiss CH1903+": "EPSG:2056",
    "RD Netherlands": "EPSG:28992",
    "GDA2020": "EPSG:7844",
    "GDA94": "EPSG:4283",
    "NZGD2000": "EPSG:2193",
    "JGD2011": "EPSG:6668",
    # Web
    "Web Mercator": "EPSG:3857",
    "Pseudo-Mercator": "EPSG:3857",
    "Google": "EPSG:3857",
}


class CRSRegistry:
    """Look-up and cache for Coordinate Reference System definitions.

    Supports EPSG codes, WKT strings, PROJ strings, and well-known aliases
    (e.g. ``"OSGB36"``, ``"Web Mercator"``).
    """

    def __init__(self) -> None:
        self._aliases: dict[str, str] = dict(_GRID_ALIASES)
        self._cache: dict[str, CRS] = {}

    # ── Public API ──────────────────────────────────────────────────────

    def resolve(self, name_or_code: str) -> str:
        """Resolve an alias or code to a canonical EPSG string.

        If the input is already an EPSG code (``"EPSG:xxxx"``) it is returned
        unchanged.  Otherwise the internal alias table is checked.
        """
        upper = name_or_code.upper().strip()
        if upper.startswith("EPSG:"):
            return name_or_code
        # Check aliases (case-insensitive)
        for alias, code in self._aliases.items():
            if alias.upper() == upper:
                return code
        # Fall back – let pyproj try to interpret it directly
        return name_or_code

    def get_crs(self, name_or_code: str) -> CRS:
        """Return a :class:`pyproj.CRS` object, with caching."""
        key = self.resolve(name_or_code)
        if key not in self._cache:
            self._cache[key] = CRS.from_user_input(key)
        return self._cache[key]

    def register_alias(self, alias: str, epsg_code: str) -> None:
        """Register a custom alias for quick lookup."""
        self._aliases[alias] = epsg_code

    def list_aliases(self) -> dict[str, str]:
        """Return the current alias table."""
        return dict(self._aliases)

    def search(self, keyword: str) -> list[dict[str, str]]:
        """Search aliases by keyword (case-insensitive)."""
        keyword = keyword.upper()
        return [
            {"alias": alias, "code": code}
            for alias, code in self._aliases.items()
            if keyword in alias.upper() or keyword in code.upper()
        ]

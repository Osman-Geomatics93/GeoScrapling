"""Fetch GNSS/GPS reference data from various services.

Supports CORS station queries, RINEX downloads, NTRIP caster discovery,
and geodetic control point searches.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scrapling.geo.models import GeoPoint


class GNSSFetcher:
    """Fetch GNSS/GPS reference data from various services."""

    # Default NGS CORS API base URL
    CORS_API = "https://geodesy.noaa.gov/corsdata"
    NGS_API = "https://geodesy.noaa.gov/api"

    def __init__(self, data_dir: str | Path = "gnss_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # ── CORS station data ───────────────────────────────────────────────

    def list_cors_stations(
        self,
        bbox: tuple[float, float, float, float] | None = None,
        network: str | None = None,
    ) -> list[dict[str, Any]]:
        """List CORS (Continuously Operating Reference Stations).

        Parameters
        ----------
        bbox : tuple, optional
            (min_lon, min_lat, max_lon, max_lat) to filter stations.
        network : str, optional
            Network name filter (e.g. ``"NOAA CORS"``).
        """
        import json
        import urllib.request

        url = f"{self.NGS_API}/cors/stations"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:  # nosec B310
                stations = json.loads(resp.read())
        except Exception:
            # Fallback for when API is unavailable
            return []

        if isinstance(stations, dict):
            stations = stations.get("stations", stations.get("data", []))

        results: list[dict[str, Any]] = []
        for st in stations:
            lat = st.get("latitude") or st.get("lat")
            lon = st.get("longitude") or st.get("lon")
            if lat is None or lon is None:
                continue

            lat, lon = float(lat), float(lon)

            if bbox:
                min_x, min_y, max_x, max_y = bbox
                if not (min_x <= lon <= max_x and min_y <= lat <= max_y):
                    continue

            if network and network.lower() not in str(st.get("network", "")).lower():
                continue

            results.append(st)

        return results

    def get_station_info(self, station_id: str) -> dict[str, Any]:
        """Get detailed information about a CORS station."""
        import json
        import urllib.request

        url = f"{self.NGS_API}/cors/station/{station_id}"
        with urllib.request.urlopen(url, timeout=30) as resp:  # nosec B310
            return json.loads(resp.read())

    def get_station_coordinates(self, station_id: str) -> GeoPoint:
        """Get the reference coordinates of a CORS station."""
        info = self.get_station_info(station_id)
        return GeoPoint(
            x=float(info.get("longitude", info.get("lon", 0))),
            y=float(info.get("latitude", info.get("lat", 0))),
            z=float(info.get("elevation", info.get("height", 0))),
            crs="EPSG:4326",
        )

    # ── RINEX observation data ──────────────────────────────────────────

    def download_rinex(
        self,
        station_id: str,
        date: str,
        output_dir: str | Path | None = None,
    ) -> Path:
        """Download a RINEX observation file.

        Parameters
        ----------
        station_id : str
            Four-character station identifier.
        date : str
            Date in ``YYYY-MM-DD`` format.
        output_dir : path, optional
            Where to save; defaults to ``self.data_dir``.
        """
        import urllib.request
        from datetime import datetime

        dt = datetime.strptime(date, "%Y-%m-%d")
        doy = dt.timetuple().tm_yday
        year = dt.year
        sid = station_id.lower()[:4]

        # Standard IGS / NOAA naming convention
        filename = f"{sid}{doy:03d}0.{str(year)[2:]}o.gz"
        url = f"{self.CORS_API}/rinex/{year}/{doy:03d}/{sid}/{filename}"

        out = Path(output_dir) if output_dir else self.data_dir
        out.mkdir(parents=True, exist_ok=True)
        dest = out / filename

        urllib.request.urlretrieve(url, str(dest))  # nosec B310
        return dest

    # ── NTRIP ───────────────────────────────────────────────────────────

    def list_ntrip_casters(self) -> list[dict[str, Any]]:
        """Return a list of known public NTRIP casters."""
        return [
            {"name": "IGS", "url": "http://igs-ip.net:2101", "country": "International"},
            {"name": "EUREF", "url": "http://euref-ip.net:2101", "country": "EU"},
            {"name": "BKG", "url": "http://products.igs-ip.net:2101", "country": "DE"},
            {"name": "UNAVCO", "url": "http://rtgps.unavco.org:2101", "country": "US"},
        ]

    def get_ntrip_sourcetable(self, caster_url: str) -> list[dict[str, Any]]:
        """Retrieve and parse an NTRIP caster source table.

        Returns a list of mountpoint dicts with ``name``, ``format``,
        ``carrier``, ``lat``, ``lon``, etc.
        """
        import urllib.request

        req = urllib.request.Request(
            caster_url,
            headers={"Ntrip-Version": "Ntrip/2.0", "User-Agent": "NTRIP GeoScrapling/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
                raw = resp.read().decode("utf-8", errors="replace")
        except Exception as exc:
            raise ConnectionError(f"Cannot reach NTRIP caster at {caster_url}: {exc}")

        entries: list[dict[str, Any]] = []
        for line in raw.splitlines():
            parts = line.split(";")
            if len(parts) < 10 or parts[0] not in ("STR", "CAS", "NET"):
                continue
            entry: dict[str, Any] = {"type": parts[0], "mountpoint": parts[1]}
            if parts[0] == "STR" and len(parts) >= 19:
                entry.update(
                    {
                        "identifier": parts[2],
                        "format": parts[3],
                        "carrier": parts[5],
                        "lat": float(parts[9]) if parts[9] else None,
                        "lon": float(parts[10]) if parts[10] else None,
                        "country": parts[7],
                    }
                )
            entries.append(entry)
        return entries

    # ── Geodetic control points ─────────────────────────────────────────

    def search_control_points(
        self,
        bbox: tuple[float, float, float, float] | None = None,
        network: str | None = None,
    ):
        """Search for geodetic control points / benchmarks.

        Returns a :class:`geopandas.GeoDataFrame` of control points.
        """
        import geopandas as gpd
        from shapely.geometry import Point

        stations = self.list_cors_stations(bbox=bbox, network=network)
        if not stations:
            return gpd.GeoDataFrame()

        geoms = []
        props = []
        for st in stations:
            lat = float(st.get("latitude", st.get("lat", 0)))
            lon = float(st.get("longitude", st.get("lon", 0)))
            geoms.append(Point(lon, lat))
            props.append(st)

        return gpd.GeoDataFrame(props, geometry=geoms, crs="EPSG:4326")

    def get_benchmark_info(self, pid: str) -> dict[str, Any]:
        """Get details for a specific geodetic benchmark by PID."""
        import json
        import urllib.request

        url = f"{self.NGS_API}/ncat/pid/{pid}"
        with urllib.request.urlopen(url, timeout=30) as resp:  # nosec B310
            return json.loads(resp.read())

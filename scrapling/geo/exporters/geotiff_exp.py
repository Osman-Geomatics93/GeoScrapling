"""GeoTIFF exporter for raster data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def geotiff_export(
    raster_data: Any,
    path: str,
    crs: str = "EPSG:4326",
    transform: Any = None,
) -> Path:
    """Write raster data (numpy array) to a GeoTIFF file.

    Parameters
    ----------
    raster_data : numpy.ndarray
        2-D or 3-D array (bands, rows, cols).
    path : str
        Output file path.
    crs : str
        Coordinate reference system.
    transform : rasterio.Affine or None
        Affine transform.  Required for georeferencing.
    """
    import rasterio
    from rasterio.crs import CRS as RioCRS
    from rasterio.transform import from_bounds

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    data = np.asarray(raster_data)
    if data.ndim == 2:
        data = data[np.newaxis, ...]  # (1, rows, cols)

    bands, height, width = data.shape
    dtype = data.dtype

    profile = {
        "driver": "GTiff",
        "dtype": str(dtype),
        "width": width,
        "height": height,
        "count": bands,
        "crs": RioCRS.from_user_input(crs),
        "compress": "deflate",
    }
    if transform is not None:
        profile["transform"] = transform

    with rasterio.open(str(out), "w", **profile) as dst:
        for i in range(bands):
            dst.write(data[i], i + 1)

    return out

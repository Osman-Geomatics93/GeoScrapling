"""Coordinate quality metadata & validation.

Re-exports :class:`~scrapling.geo.models.CoordinateQuality` and provides
additional quality assessment helpers.
"""

from __future__ import annotations

from scrapling.geo.models import CoordinateQuality

__all__ = ["CoordinateQuality", "estimate_precision", "precision_to_accuracy"]


def estimate_precision(value: float) -> int:
    """Estimate the number of meaningful decimal places in a float.

    >>> estimate_precision(40.7128)
    4
    >>> estimate_precision(40.0)
    0
    """
    text = f"{value:.15g}"
    if "." not in text:
        return 0
    return len(text.split(".")[1].rstrip("0"))


def precision_to_accuracy(decimal_places: int, is_geographic: bool = True) -> float:
    """Rough mapping from decimal-degree precision to ground accuracy in metres.

    For geographic CRS (degrees):
      - 1 decimal place  ≈ 11 km
      - 3 decimal places ≈ 110 m
      - 5 decimal places ≈ 1.1 m
      - 7 decimal places ≈ 0.011 m

    For projected CRS (metres) the accuracy is simply ``10**-decimal_places``.
    """
    if is_geographic:
        # 1 degree ≈ 111 320 m at the equator
        return 111_320.0 / (10**decimal_places)
    return 10.0 ** (-decimal_places)

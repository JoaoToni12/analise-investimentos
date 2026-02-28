from __future__ import annotations

from engine.models import Asset, Band, ZoneStatus


def compute_band(target_weight: float, relative_pct: float, absolute_pp: float) -> Band:
    """Create a tolerance band around a target weight.

    Args:
        target_weight: target allocation in % (e.g. 10.0 for 10%)
        relative_pct: relative tolerance as a fraction (e.g. 0.10 for ±10% of target)
        absolute_pp:  absolute tolerance in percentage points (e.g. 2.0 for ±2pp)
    """
    return Band(target_weight=target_weight, relative_pct=relative_pct, absolute_pp=absolute_pp)


def classify_zone(current_weight: float, band: Band) -> ZoneStatus:
    """Classify an asset's status based on its current weight vs band."""
    if current_weight < band.lower_bound:
        return ZoneStatus.BUY
    if current_weight > band.upper_bound:
        return ZoneStatus.SELL
    return ZoneStatus.HOLD


def classify_all(
    assets: list[Asset],
    relative_pct: float,
    absolute_pp: float,
) -> dict[str, tuple[ZoneStatus, Band]]:
    """Classify every asset and return status + band per ticker."""
    result: dict[str, tuple[ZoneStatus, Band]] = {}
    for a in assets:
        band = compute_band(a.target_weight, relative_pct, absolute_pp)
        status = classify_zone(a.current_weight, band)
        result[a.ticker] = (status, band)
    return result

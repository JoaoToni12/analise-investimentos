from __future__ import annotations

from engine.models import Asset, AssetClass


def compute_portfolio_value(assets: list[Asset]) -> float:
    """Total market value of all assets."""
    return sum(a.current_value for a in assets)


def compute_weights(assets: list[Asset]) -> dict[str, float]:
    """Compute current weight (%) of each asset relative to total portfolio value."""
    total = compute_portfolio_value(assets)
    if total <= 0:
        return {a.ticker: 0.0 for a in assets}
    return {a.ticker: (a.current_value / total) * 100.0 for a in assets}


def compute_class_weights(assets: list[Asset]) -> dict[AssetClass, float]:
    """Aggregate weights by asset class."""
    total = compute_portfolio_value(assets)
    if total <= 0:
        return {}
    class_values: dict[AssetClass, float] = {}
    for a in assets:
        class_values[a.asset_class] = class_values.get(a.asset_class, 0.0) + a.current_value
    return {cls: (val / total) * 100.0 for cls, val in class_values.items()}


def compute_gaps(assets: list[Asset]) -> dict[str, float]:
    """Delta between target weight and current weight.

    Positive gap = underweight (needs buying).
    Negative gap = overweight (may need selling).
    """
    weights = compute_weights(assets)
    return {a.ticker: a.target_weight - weights.get(a.ticker, 0.0) for a in assets}


def enrich_weights(assets: list[Asset]) -> list[Asset]:
    """Update current_weight on each asset in-place and return the list."""
    weights = compute_weights(assets)
    for a in assets:
        a.current_weight = weights.get(a.ticker, 0.0)
    return assets

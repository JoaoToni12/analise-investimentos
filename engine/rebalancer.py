from __future__ import annotations

import math
from collections import defaultdict

from engine.models import Asset, AssetClass, Band, Order, OrderAction, ZoneStatus
from engine.portfolio import compute_portfolio_value


def compute_class_targets(assets: list[Asset]) -> dict[AssetClass, float]:
    """Sum target weights by asset class."""
    targets: dict[AssetClass, float] = defaultdict(float)
    for a in assets:
        targets[a.asset_class] += a.target_weight
    return dict(targets)


def compute_rebalancing(
    assets: list[Asset],
    cash_injection: float,
    zones: dict[str, tuple[ZoneStatus, Band]],
    max_orders: int = 5,
) -> tuple[list[Order], float]:
    """Two-layer rebalancing concentrated on the top N most underweight assets.

    Layer 1: Distribute cash proportionally across asset classes.
    Layer 2: Within each class, rank assets by gap and select only the
             top candidates (limited by max_orders globally).

    Returns:
        orders: list of Order objects (at most max_orders buys)
        residual_cash: unallocated cash after all buys
    """
    v_current = compute_portfolio_value(assets)
    v_projected = v_current + cash_injection

    if v_projected <= 0:
        return [], cash_injection

    # --- Layer 1: Allocate budget across classes proportionally ---
    assets_by_class: dict[AssetClass, list[Asset]] = defaultdict(list)
    for a in assets:
        assets_by_class[a.asset_class].append(a)

    # --- Layer 2: Within each class, rank by RELATIVE gap ---
    ranked: list[tuple[Asset, float, float]] = []
    for a in assets:
        if a.current_price <= 0 or a.target_weight <= 0:
            continue
        target_val = (a.target_weight / 100.0) * v_projected
        delta = target_val - a.current_value
        if delta <= 0:
            continue
        relative_gap = delta / target_val
        status = zones.get(a.ticker, (ZoneStatus.HOLD, None))[0]
        priority = relative_gap * (2.0 if status == ZoneStatus.BUY else 1.0)
        ranked.append((a, delta, priority))

    ranked.sort(key=lambda x: -x[2])

    # Select top N candidates, ensuring class diversity (at least 1 per class if available)
    top_candidates: list[tuple[Asset, float]] = []
    seen_classes: set[AssetClass] = set()
    remaining_slots = max_orders

    # First pass: 1 representative per class (highest priority in that class)
    for a, delta, _prio in ranked:
        if a.asset_class not in seen_classes and remaining_slots > 0:
            top_candidates.append((a, delta))
            seen_classes.add(a.asset_class)
            remaining_slots -= 1

    # Second pass: fill remaining slots with next highest priority regardless of class
    selected_tickers = {a.ticker for a, _ in top_candidates}
    for a, delta, _prio in ranked:
        if remaining_slots <= 0:
            break
        if a.ticker not in selected_tickers:
            top_candidates.append((a, delta))
            selected_tickers.add(a.ticker)
            remaining_slots -= 1
    if not top_candidates:
        return _compute_sells_only(assets, v_projected, zones, cash_injection)

    # --- Distribute budget proportionally to each candidate's gap ---
    total_priority = sum(p for _, p in top_candidates)
    orders: list[Order] = []
    remaining_cash = cash_injection

    for a, priority in top_candidates:
        if remaining_cash <= 0:
            break
        share = (priority / total_priority) if total_priority > 0 else (1.0 / len(top_candidates))
        budget = cash_injection * share
        budget = min(budget, remaining_cash)
        qty = math.floor(budget / a.current_price)
        if qty > 0:
            orders.append(Order(ticker=a.ticker, action=OrderAction.BUY, quantity=qty, price=a.current_price))
            remaining_cash -= qty * a.current_price

    # --- Sweep: use leftover cash to buy more of the top candidates ---
    for a, _ in top_candidates:
        if remaining_cash < a.current_price:
            continue
        extra_qty = math.floor(remaining_cash / a.current_price)
        if extra_qty <= 0:
            continue
        existing = next((o for o in orders if o.ticker == a.ticker), None)
        if existing:
            existing.quantity += extra_qty
        else:
            orders.append(Order(ticker=a.ticker, action=OrderAction.BUY, quantity=extra_qty, price=a.current_price))
        remaining_cash -= extra_qty * a.current_price

    # --- Sell orders (last resort) ---
    sell_orders = _compute_sells(assets, v_projected, zones)
    for order in sell_orders[:max_orders]:
        orders.append(order)
        remaining_cash += order.amount

    return orders, max(remaining_cash, 0)


def _compute_sells(
    assets: list[Asset],
    v_projected: float,
    zones: dict[str, tuple[ZoneStatus, Band]],
) -> list[Order]:
    """Sell orders only for severe band overflow."""
    orders: list[Order] = []
    for a in assets:
        status, band = zones.get(a.ticker, (ZoneStatus.HOLD, None))
        if status != ZoneStatus.SELL or band is None:
            continue
        if a.current_price <= 0:
            continue

        target_at_upper = (band.upper_bound / 100.0) * v_projected
        excess = a.current_value - target_at_upper
        if excess <= 0:
            continue

        qty = math.floor(excess / a.current_price)
        if qty > 0:
            orders.append(Order(ticker=a.ticker, action=OrderAction.SELL, quantity=qty, price=a.current_price))

    return orders


def _compute_sells_only(
    assets: list[Asset],
    v_projected: float,
    zones: dict[str, tuple[ZoneStatus, Band]],
    cash: float,
) -> tuple[list[Order], float]:
    """When no buy candidates exist, only process sells."""
    orders = _compute_sells(assets, v_projected, zones)
    residual = cash + sum(o.amount for o in orders)
    return orders, max(residual, 0)

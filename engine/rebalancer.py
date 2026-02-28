from __future__ import annotations

import math
from collections import defaultdict

from engine.models import Asset, AssetClass, Band, Order, OrderAction, ZoneStatus
from engine.portfolio import compute_class_weights, compute_portfolio_value


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
) -> tuple[list[Order], float]:
    """Two-layer rebalancing: first allocate across classes, then within each class.

    Layer 1: Distribute cash proportionally to class-level deficits.
    Layer 2: Within each class, buy the most underweight assets first.

    Returns:
        orders: list of Order objects
        residual_cash: unallocated cash after all buys
    """
    v_current = compute_portfolio_value(assets)
    v_projected = v_current + cash_injection

    if v_projected <= 0:
        return [], cash_injection

    # --- Layer 1: Class-level allocation ---
    class_targets = compute_class_targets(assets)
    class_weights = compute_class_weights(assets)
    assets_by_class: dict[AssetClass, list[Asset]] = defaultdict(list)
    for a in assets:
        assets_by_class[a.asset_class].append(a)

    class_deficits: dict[AssetClass, float] = {}
    for cls, target in class_targets.items():
        current = class_weights.get(cls, 0.0)
        gap = target - current
        if gap > 0:
            class_deficits[cls] = gap

    total_deficit = sum(class_deficits.values())
    class_cash: dict[AssetClass, float] = {}
    if total_deficit > 0:
        for cls, deficit in class_deficits.items():
            class_cash[cls] = cash_injection * (deficit / total_deficit)
    else:
        for cls in class_targets:
            class_cash[cls] = cash_injection * (class_targets[cls] / 100.0) if sum(class_targets.values()) > 0 else 0

    # --- Layer 2: Within-class allocation ---
    orders: list[Order] = []
    remaining_cash = cash_injection

    for cls in sorted(class_cash, key=lambda c: -class_cash.get(c, 0)):
        budget = class_cash.get(cls, 0)
        if budget <= 0:
            continue

        cls_assets = assets_by_class.get(cls, [])
        if not cls_assets:
            continue

        buy_list = _compute_class_buys(cls_assets, budget, v_projected, zones)
        for order in buy_list:
            orders.append(order)
            remaining_cash -= order.amount

    # --- Phase 3: Sell orders (last resort) ---
    sell_orders = _compute_sells(assets, v_projected, zones)
    for order in sell_orders:
        orders.append(order)
        remaining_cash += order.amount

    return orders, max(remaining_cash, 0)


def _compute_class_buys(
    cls_assets: list[Asset],
    budget: float,
    v_projected: float,
    zones: dict[str, tuple[ZoneStatus, Band]],
) -> list[Order]:
    """Allocate budget within a single asset class to the most underweight assets."""
    deltas: list[tuple[Asset, float]] = []
    for a in cls_assets:
        target_val = (a.target_weight / 100.0) * v_projected
        delta = target_val - a.current_value
        status = zones.get(a.ticker, (ZoneStatus.HOLD, None))[0]
        if delta > 0 and status != ZoneStatus.HOLD:
            deltas.append((a, delta))
        elif status == ZoneStatus.BUY:
            deltas.append((a, max(delta, 0.01)))

    deltas.sort(key=lambda x: -x[1])

    orders: list[Order] = []
    cash_left = budget
    for a, delta in deltas:
        if cash_left <= 0:
            break
        if a.current_price <= 0:
            continue
        spend = min(delta, cash_left)
        qty = math.floor(spend / a.current_price)
        if qty > 0:
            orders.append(Order(ticker=a.ticker, action=OrderAction.BUY, quantity=qty, price=a.current_price))
            cash_left -= qty * a.current_price

    return orders


def _compute_sells(
    assets: list[Asset],
    v_projected: float,
    zones: dict[str, tuple[ZoneStatus, Band]],
) -> list[Order]:
    """Sell orders only for severe band overflow that can't be diluted."""
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

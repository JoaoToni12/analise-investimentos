from __future__ import annotations

import math

from engine.models import Asset, Band, Order, OrderAction, ZoneStatus
from engine.portfolio import compute_portfolio_value


def compute_rebalancing(
    assets: list[Asset],
    cash_injection: float,
    zones: dict[str, tuple[ZoneStatus, Band]],
) -> tuple[list[Order], float]:
    """Compute buy/sell orders to rebalance the portfolio with a cash injection.

    Returns:
        orders: list of Order objects
        residual_cash: unallocated cash after all buys
    """
    v_current = compute_portfolio_value(assets)
    v_projected = v_current + cash_injection

    if v_projected <= 0:
        return [], cash_injection

    asset_map = {a.ticker: a for a in assets}
    orders: list[Order] = []

    deltas: list[tuple[str, float]] = []
    for a in assets:
        target_nocional = (a.target_weight / 100.0) * v_projected
        delta = target_nocional - a.current_value
        deltas.append((a.ticker, delta))

    # --- Phase 1: Buy orders (cash injection only) ---
    buy_candidates = [
        (ticker, delta)
        for ticker, delta in deltas
        if delta > 0 and zones.get(ticker, (ZoneStatus.HOLD, None))[0] != ZoneStatus.HOLD
    ]
    # Also include BUY-zone assets even if delta is small
    for ticker, delta in deltas:
        status = zones.get(ticker, (ZoneStatus.HOLD, None))[0]
        if status == ZoneStatus.BUY and not any(t == ticker for t, _ in buy_candidates):
            buy_candidates.append((ticker, max(delta, 0.01)))

    buy_candidates.sort(key=lambda x: -x[1])

    remaining_cash = cash_injection
    for ticker, delta in buy_candidates:
        if remaining_cash <= 0:
            break
        a = asset_map[ticker]
        if a.current_price <= 0:
            continue
        max_spend = min(delta, remaining_cash)
        qty = math.floor(max_spend / a.current_price)
        if qty > 0:
            orders.append(Order(ticker=ticker, action=OrderAction.BUY, quantity=qty, price=a.current_price))
            remaining_cash -= qty * a.current_price

    # --- Phase 2: Sell orders (last resort — only for severe band overflow) ---
    for ticker, delta in deltas:
        if delta >= 0:
            continue
        status, band = zones.get(ticker, (ZoneStatus.HOLD, None))
        if status != ZoneStatus.SELL or band is None:
            continue

        a = asset_map[ticker]
        if a.current_price <= 0:
            continue

        # Only sell enough to bring weight back to upper bound
        current_value_in_portfolio = a.current_value
        target_value_at_upper = (band.upper_bound / 100.0) * v_projected
        excess = current_value_in_portfolio - target_value_at_upper
        if excess <= 0:
            continue

        # Check if the buy phase + projected dilution already solved it
        post_buy_total = v_projected  # approximation
        new_weight = (a.current_value / post_buy_total) * 100.0 if post_buy_total > 0 else 0
        if new_weight <= band.upper_bound:
            continue

        qty = math.floor(excess / a.current_price)
        if qty > 0:
            orders.append(Order(ticker=ticker, action=OrderAction.SELL, quantity=qty, price=a.current_price))
            remaining_cash += qty * a.current_price

    return orders, remaining_cash

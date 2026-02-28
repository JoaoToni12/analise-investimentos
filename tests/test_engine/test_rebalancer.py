from engine.grey_zones import classify_all
from engine.models import Asset, AssetClass, OrderAction
from engine.portfolio import enrich_weights
from engine.rebalancer import compute_rebalancing


def _build(
    data: list[tuple[str, float, float, float, str]],
    relative: float = 0.20,
    absolute: float = 1.5,
) -> tuple[list[Asset], dict]:
    assets = [
        Asset(ticker=t, asset_class=AssetClass.from_str(c), quantity=q, avg_price=p, current_price=p, target_weight=tw)
        for t, q, p, tw, c in data
    ]
    assets = enrich_weights(assets)
    zones = classify_all(assets, relative, absolute)
    return assets, zones


class TestMaxOrders:
    def test_limits_to_max_orders(self):
        assets, zones = _build(
            [
                ("A", 1, 10, 20, "ACAO"),
                ("B", 1, 10, 20, "ACAO"),
                ("C", 1, 10, 20, "FII"),
                ("D", 1, 10, 20, "FII"),
                ("E", 1, 10, 20, "CRYPTO"),
            ],
            relative=0.20,
            absolute=30.0,
        )
        orders, _ = compute_rebalancing(assets, 5000.0, zones, max_orders=3)
        buy_tickers = {o.ticker for o in orders if o.action == OrderAction.BUY}
        assert len(buy_tickers) <= 3

    def test_concentrates_budget(self):
        assets, zones = _build(
            [
                ("A", 1, 50, 50, "ACAO"),
                ("B", 1, 50, 50, "FII"),
            ],
            relative=0.20,
            absolute=30.0,
        )
        orders, residual = compute_rebalancing(assets, 1000.0, zones, max_orders=2)
        total_spent = sum(o.amount for o in orders)
        assert total_spent > 900  # most of the budget should be used

    def test_respects_max_one(self):
        assets, zones = _build(
            [
                ("A", 1, 10, 30, "ACAO"),
                ("B", 1, 10, 30, "ACAO"),
                ("C", 1, 10, 40, "FII"),
            ],
            relative=0.20,
            absolute=30.0,
        )
        orders, _ = compute_rebalancing(assets, 500.0, zones, max_orders=1)
        buy_tickers = {o.ticker for o in orders if o.action == OrderAction.BUY}
        assert len(buy_tickers) == 1


class TestBuyOrders:
    def test_floor_division(self):
        assets, zones = _build([("A", 1, 100, 50, "ACAO"), ("B", 1, 100, 50, "FII")], absolute=30.0)
        orders, _ = compute_rebalancing(assets, 150.0, zones, max_orders=5)
        for o in orders:
            assert o.quantity == int(o.quantity)

    def test_prioritizes_most_underweight(self):
        assets, zones = _build(
            [
                ("A", 1, 50, 60, "ACAO"),
                ("B", 5, 50, 20, "ACAO"),
                ("C", 10, 50, 20, "FII"),
            ],
            relative=0.20,
            absolute=20.0,
        )
        orders, _ = compute_rebalancing(assets, 500.0, zones, max_orders=2)
        if orders:
            assert orders[0].ticker == "A"  # most underweight gets priority


class TestSellOrders:
    def test_no_sell_within_bands(self):
        assets, zones = _build([("A", 5, 100, 50, "ACAO"), ("B", 5, 100, 50, "FII")])
        orders, _ = compute_rebalancing(assets, 0.0, zones)
        assert all(o.action != OrderAction.SELL for o in orders)

    def test_sell_severe_overflow(self):
        assets, zones = _build(
            [
                ("A", 90, 100, 10, "ACAO"),
                ("B", 10, 100, 90, "FII"),
            ],
            relative=0.10,
            absolute=1.0,
        )
        orders, _ = compute_rebalancing(assets, 0.0, zones)
        sells = [o for o in orders if o.action == OrderAction.SELL]
        assert len(sells) > 0
        assert sells[0].ticker == "A"


class TestResidual:
    def test_nonnegative(self):
        assets, zones = _build([("A", 10, 100, 50, "ACAO"), ("B", 10, 100, 50, "FII")])
        _, residual = compute_rebalancing(assets, 1000.0, zones)
        assert residual >= 0

    def test_zero_injection(self):
        assets, zones = _build([("A", 10, 100, 50, "ACAO"), ("B", 10, 100, 50, "FII")])
        _, residual = compute_rebalancing(assets, 0.0, zones)
        assert residual == 0.0

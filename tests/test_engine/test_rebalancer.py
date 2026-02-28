from engine.grey_zones import classify_all
from engine.models import Asset, AssetClass, OrderAction
from engine.portfolio import enrich_weights
from engine.rebalancer import compute_rebalancing


def _build_assets_and_zones(
    assets_data: list[tuple[str, float, float, float]],
    relative: float = 0.10,
    absolute: float = 1.0,
) -> tuple[list[Asset], dict]:
    """Helper: build assets from (ticker, qty, price, target) tuples, enrich, classify."""
    assets = [
        Asset(ticker=t, asset_class=AssetClass.ACAO, quantity=q, avg_price=p, current_price=p, target_weight=tw)
        for t, q, p, tw in assets_data
    ]
    assets = enrich_weights(assets)
    zones = classify_all(assets, relative, absolute)
    return assets, zones


class TestBuyOrders:
    def test_buy_only_with_positive_cash(self):
        # A is deeply underweight -> BUY; B and C are slightly over but within wide band -> HOLD
        assets, zones = _build_assets_and_zones(
            [
                ("A", 1, 100, 50),  # 10% weight, target 50% -> BUY (below lower=15)
                ("B", 4, 100, 25),  # 40% weight, target 25% -> HOLD (under upper=57.5)
                ("C", 5, 100, 25),  # 50% weight, target 25% -> HOLD (under upper=57.5)
            ],
            relative=0.10,
            absolute=30.0,
        )
        orders, residual = compute_rebalancing(assets, 500.0, zones)
        buy_orders = [o for o in orders if o.action == OrderAction.BUY]
        sell_orders = [o for o in orders if o.action == OrderAction.SELL]
        assert len(buy_orders) > 0
        assert len(sell_orders) == 0

    def test_floor_division_quantity(self):
        assets, zones = _build_assets_and_zones(
            [
                ("A", 1, 100, 80),
                ("B", 10, 100, 20),
            ]
        )
        orders, _ = compute_rebalancing(assets, 150.0, zones)
        for o in orders:
            assert o.quantity == int(o.quantity)
            assert o.quantity >= 0

    def test_priority_most_underweight_first(self):
        assets, zones = _build_assets_and_zones(
            [
                ("A", 1, 50, 60),  # very underweight
                ("B", 5, 50, 30),  # less underweight
                ("C", 10, 50, 10),  # roughly balanced
            ]
        )
        orders, _ = compute_rebalancing(assets, 200.0, zones)
        buy_orders = [o for o in orders if o.action == OrderAction.BUY]
        if len(buy_orders) >= 2:
            assert buy_orders[0].amount >= buy_orders[1].amount


class TestSellOrders:
    def test_sell_only_when_band_overflow(self):
        assets, zones = _build_assets_and_zones(
            [
                ("A", 1, 100, 10),  # 10% value, target 10% -> balanced
                ("B", 9, 100, 90),  # 90% value, target 90% -> balanced
            ]
        )
        orders, _ = compute_rebalancing(assets, 0.0, zones)
        sell_orders = [o for o in orders if o.action == OrderAction.SELL]
        assert len(sell_orders) == 0

    def test_sell_with_severe_overflow(self):
        # A holds 90% of value but target is 10% -> way over upper band
        assets = [
            Asset(
                ticker="A",
                asset_class=AssetClass.ACAO,
                quantity=90,
                avg_price=100,
                current_price=100,
                target_weight=10.0,
            ),
            Asset(
                ticker="B",
                asset_class=AssetClass.ACAO,
                quantity=10,
                avg_price=100,
                current_price=100,
                target_weight=90.0,
            ),
        ]
        assets = enrich_weights(assets)
        zones = classify_all(assets, 0.10, 1.0)
        orders, _ = compute_rebalancing(assets, 0.0, zones)
        sell_orders = [o for o in orders if o.action == OrderAction.SELL]
        assert len(sell_orders) > 0
        assert sell_orders[0].ticker == "A"


class TestResidualCash:
    def test_residual_cash_returned(self):
        assets, zones = _build_assets_and_zones(
            [
                ("A", 10, 100, 50),
                ("B", 10, 100, 50),
            ]
        )
        _, residual = compute_rebalancing(assets, 1000.0, zones)
        assert residual >= 0

    def test_zero_cash_injection(self):
        assets, zones = _build_assets_and_zones(
            [
                ("A", 10, 100, 50),
                ("B", 10, 100, 50),
            ]
        )
        orders, residual = compute_rebalancing(assets, 0.0, zones)
        assert residual == 0.0

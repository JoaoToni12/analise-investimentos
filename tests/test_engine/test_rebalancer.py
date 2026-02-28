from engine.grey_zones import classify_all
from engine.models import Asset, AssetClass, OrderAction
from engine.portfolio import enrich_weights
from engine.rebalancer import compute_class_targets, compute_rebalancing


def _build_assets_and_zones(
    assets_data: list[tuple[str, float, float, float, str]],
    relative: float = 0.20,
    absolute: float = 1.5,
) -> tuple[list[Asset], dict]:
    """Helper: build assets from (ticker, qty, price, target, class) tuples."""
    assets = [
        Asset(
            ticker=t,
            asset_class=AssetClass.from_str(c),
            quantity=q,
            avg_price=p,
            current_price=p,
            target_weight=tw,
        )
        for t, q, p, tw, c in assets_data
    ]
    assets = enrich_weights(assets)
    zones = classify_all(assets, relative, absolute)
    return assets, zones


class TestClassTargets:
    def test_sums_by_class(self):
        assets = [
            Asset(ticker="A", asset_class=AssetClass.ACAO, quantity=1, avg_price=100, target_weight=10),
            Asset(ticker="B", asset_class=AssetClass.ACAO, quantity=1, avg_price=100, target_weight=15),
            Asset(ticker="C", asset_class=AssetClass.FII, quantity=1, avg_price=100, target_weight=25),
        ]
        targets = compute_class_targets(assets)
        assert targets[AssetClass.ACAO] == 25.0
        assert targets[AssetClass.FII] == 25.0


class TestTwoLayerRebalancing:
    def test_allocates_to_underweight_class(self):
        assets, zones = _build_assets_and_zones(
            [
                ("A", 8, 100, 30, "ACAO"),  # ACAO class: 40%, target 30%
                ("B", 12, 100, 30, "FII"),  # FII class: 60%, target 30%
                ("C", 0, 100, 40, "TESOURO"),  # TESOURO: 0%, target 40% — most underweight
            ],
            relative=0.20,
            absolute=30.0,
        )
        orders, _ = compute_rebalancing(assets, 1000.0, zones)
        buy_tickers = {o.ticker for o in orders if o.action == OrderAction.BUY}
        assert "C" in buy_tickers

    def test_buy_only_no_sell_within_bands(self):
        assets, zones = _build_assets_and_zones(
            [
                ("A", 5, 100, 50, "ACAO"),
                ("B", 5, 100, 50, "FII"),
            ],
            relative=0.20,
            absolute=30.0,
        )
        orders, residual = compute_rebalancing(assets, 500.0, zones)
        sell_orders = [o for o in orders if o.action == OrderAction.SELL]
        assert len(sell_orders) == 0

    def test_floor_division_quantity(self):
        assets, zones = _build_assets_and_zones(
            [
                ("A", 1, 100, 50, "ACAO"),
                ("B", 1, 100, 50, "FII"),
            ],
            relative=0.20,
            absolute=30.0,
        )
        orders, _ = compute_rebalancing(assets, 150.0, zones)
        for o in orders:
            assert o.quantity == int(o.quantity)

    def test_priority_within_class(self):
        assets, zones = _build_assets_and_zones(
            [
                ("A", 1, 50, 40, "ACAO"),  # very underweight
                ("B", 5, 50, 30, "ACAO"),  # less underweight
                ("C", 10, 50, 30, "FII"),
            ],
            relative=0.20,
            absolute=20.0,
        )
        orders, _ = compute_rebalancing(assets, 500.0, zones)
        acao_buys = [o for o in orders if o.ticker in ("A", "B") and o.action == OrderAction.BUY]
        if len(acao_buys) >= 2:
            assert acao_buys[0].amount >= acao_buys[1].amount


class TestSellOrders:
    def test_no_sell_when_within_bands(self):
        assets, zones = _build_assets_and_zones(
            [
                ("A", 5, 100, 50, "ACAO"),
                ("B", 5, 100, 50, "FII"),
            ]
        )
        orders, _ = compute_rebalancing(assets, 0.0, zones)
        sell_orders = [o for o in orders if o.action == OrderAction.SELL]
        assert len(sell_orders) == 0

    def test_sell_with_severe_overflow(self):
        assets, zones = _build_assets_and_zones(
            [
                ("A", 90, 100, 10, "ACAO"),
                ("B", 10, 100, 90, "FII"),
            ],
            relative=0.10,
            absolute=1.0,
        )
        orders, _ = compute_rebalancing(assets, 0.0, zones)
        sell_orders = [o for o in orders if o.action == OrderAction.SELL]
        assert len(sell_orders) > 0
        assert sell_orders[0].ticker == "A"


class TestResidualCash:
    def test_residual_nonnegative(self):
        assets, zones = _build_assets_and_zones(
            [
                ("A", 10, 100, 50, "ACAO"),
                ("B", 10, 100, 50, "FII"),
            ]
        )
        _, residual = compute_rebalancing(assets, 1000.0, zones)
        assert residual >= 0

    def test_zero_injection_zero_residual(self):
        assets, zones = _build_assets_and_zones(
            [
                ("A", 10, 100, 50, "ACAO"),
                ("B", 10, 100, 50, "FII"),
            ]
        )
        orders, residual = compute_rebalancing(assets, 0.0, zones)
        assert residual == 0.0

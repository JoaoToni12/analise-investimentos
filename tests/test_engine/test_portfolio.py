from engine.models import Asset, AssetClass
from engine.portfolio import (
    compute_class_weights,
    compute_gaps,
    compute_portfolio_value,
    compute_weights,
    enrich_weights,
)


def _make_asset(ticker: str, qty: float, price: float, target: float, cls: AssetClass = AssetClass.ACAO) -> Asset:
    return Asset(
        ticker=ticker, asset_class=cls, quantity=qty, avg_price=price, current_price=price, target_weight=target
    )


class TestComputePortfolioValue:
    def test_correct_sum(self):
        assets = [_make_asset("A", 10, 100, 50), _make_asset("B", 20, 50, 50)]
        assert compute_portfolio_value(assets) == 2000.0

    def test_empty_portfolio(self):
        assert compute_portfolio_value([]) == 0.0

    def test_zero_price(self):
        assets = [_make_asset("A", 100, 0, 100)]
        assert compute_portfolio_value(assets) == 0.0


class TestComputeWeights:
    def test_weights_sum_to_one_hundred(self):
        assets = [_make_asset("A", 10, 100, 50), _make_asset("B", 10, 100, 50)]
        weights = compute_weights(assets)
        assert abs(sum(weights.values()) - 100.0) < 0.01

    def test_equal_values_equal_weights(self):
        assets = [_make_asset("A", 10, 100, 50), _make_asset("B", 10, 100, 50)]
        weights = compute_weights(assets)
        assert abs(weights["A"] - 50.0) < 0.01
        assert abs(weights["B"] - 50.0) < 0.01

    def test_zero_total_returns_zeros(self):
        assets = [_make_asset("A", 0, 0, 50)]
        weights = compute_weights(assets)
        assert weights["A"] == 0.0


class TestComputeClassWeights:
    def test_aggregation_by_class(self):
        assets = [
            _make_asset("A", 10, 100, 30, AssetClass.ACAO),
            _make_asset("B", 10, 100, 30, AssetClass.ACAO),
            _make_asset("C", 10, 100, 40, AssetClass.FII),
        ]
        class_w = compute_class_weights(assets)
        assert abs(class_w[AssetClass.ACAO] - 66.67) < 0.1
        assert abs(class_w[AssetClass.FII] - 33.33) < 0.1


class TestComputeGaps:
    def test_positive_gap_means_underweight(self):
        assets = [_make_asset("A", 10, 100, 80), _make_asset("B", 10, 100, 20)]
        gaps = compute_gaps(assets)
        assert gaps["A"] > 0  # target 80, actual 50 -> underweight

    def test_negative_gap_means_overweight(self):
        assets = [_make_asset("A", 10, 100, 20), _make_asset("B", 10, 100, 80)]
        gaps = compute_gaps(assets)
        assert gaps["A"] < 0  # target 20, actual 50 -> overweight


class TestEnrichWeights:
    def test_enriches_current_weight(self):
        assets = [_make_asset("A", 10, 100, 50), _make_asset("B", 10, 100, 50)]
        enriched = enrich_weights(assets)
        assert abs(enriched[0].current_weight - 50.0) < 0.01

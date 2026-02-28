import pytest

from engine.grey_zones import classify_all, classify_zone, compute_band
from engine.models import Asset, AssetClass, ZoneStatus


class TestComputeBand:
    def test_relative_only(self):
        band = compute_band(10.0, 0.10, 0.0)
        assert band.lower_bound == pytest.approx(9.0)
        assert band.upper_bound == pytest.approx(11.0)

    def test_absolute_only(self):
        band = compute_band(10.0, 0.0, 2.0)
        assert band.lower_bound == pytest.approx(8.0)
        assert band.upper_bound == pytest.approx(12.0)

    def test_combined(self):
        band = compute_band(10.0, 0.10, 1.0)
        assert band.lower_bound == pytest.approx(8.0)
        assert band.upper_bound == pytest.approx(12.0)

    def test_lower_bound_clamp_zero(self):
        band = compute_band(1.0, 0.50, 2.0)
        assert band.lower_bound == 0.0

    def test_zero_target(self):
        band = compute_band(0.0, 0.10, 0.5)
        assert band.lower_bound == 0.0
        assert band.upper_bound == pytest.approx(0.5)


class TestClassifyZone:
    def test_buy_below_lower(self):
        band = compute_band(10.0, 0.10, 1.0)
        assert classify_zone(7.0, band) == ZoneStatus.BUY

    def test_sell_above_upper(self):
        band = compute_band(10.0, 0.10, 1.0)
        assert classify_zone(13.0, band) == ZoneStatus.SELL

    def test_hold_within_band(self):
        band = compute_band(10.0, 0.10, 1.0)
        assert classify_zone(10.0, band) == ZoneStatus.HOLD
        assert classify_zone(8.5, band) == ZoneStatus.HOLD
        assert classify_zone(11.5, band) == ZoneStatus.HOLD

    def test_at_boundary_is_hold(self):
        band = compute_band(10.0, 0.10, 1.0)
        assert classify_zone(8.0, band) == ZoneStatus.HOLD
        assert classify_zone(12.0, band) == ZoneStatus.HOLD


class TestClassifyAll:
    def test_classifies_multiple_assets(self):
        base = {
            "asset_class": AssetClass.ACAO,
            "quantity": 1,
            "avg_price": 1,
            "current_price": 1,
            "target_weight": 10.0,
        }
        assets = [
            Asset(ticker="A", **base, current_weight=5.0),
            Asset(ticker="B", **base, current_weight=10.0),
            Asset(ticker="C", **base, current_weight=15.0),
        ]
        result = classify_all(assets, 0.10, 1.0)
        assert result["A"][0] == ZoneStatus.BUY
        assert result["B"][0] == ZoneStatus.HOLD
        assert result["C"][0] == ZoneStatus.SELL

from engine.models import Asset, AssetClass, Band, Order, OrderAction, ZoneStatus


class TestAssetClass:
    def test_from_str_valid(self):
        assert AssetClass.from_str("ACAO") == AssetClass.ACAO
        assert AssetClass.from_str("fii") == AssetClass.FII
        assert AssetClass.from_str("Crypto") == AssetClass.CRYPTO

    def test_from_str_unknown_defaults_to_acao(self):
        assert AssetClass.from_str("UNKNOWN") == AssetClass.ACAO


class TestAsset:
    def test_current_value(self):
        a = Asset(ticker="TEST", asset_class=AssetClass.ACAO, quantity=100, avg_price=10.0, current_price=15.0)
        assert a.current_value == 1500.0

    def test_cost_basis(self):
        a = Asset(ticker="TEST", asset_class=AssetClass.ACAO, quantity=100, avg_price=10.0, current_price=15.0)
        assert a.cost_basis == 1000.0

    def test_pnl(self):
        a = Asset(ticker="TEST", asset_class=AssetClass.ACAO, quantity=100, avg_price=10.0, current_price=15.0)
        assert a.pnl == 500.0


class TestBand:
    def test_band_bounds(self):
        band = Band(target_weight=10.0, relative_pct=0.10, absolute_pp=1.0)
        assert band.lower_bound == 10.0 - 10.0 * 0.10 - 1.0  # 8.0
        assert band.upper_bound == 10.0 + 10.0 * 0.10 + 1.0  # 12.0

    def test_lower_bound_clamped_at_zero(self):
        band = Band(target_weight=1.0, relative_pct=0.50, absolute_pp=2.0)
        assert band.lower_bound == 0.0


class TestOrder:
    def test_amount(self):
        order = Order(ticker="TEST", action=OrderAction.BUY, quantity=10, price=25.0)
        assert order.amount == 250.0


class TestEnums:
    def test_zone_status_values(self):
        assert ZoneStatus.BUY.value == "BUY"
        assert ZoneStatus.HOLD.value == "HOLD"
        assert ZoneStatus.SELL.value == "SELL"

    def test_order_action_values(self):
        assert OrderAction.BUY.value == "BUY"
        assert OrderAction.SELL.value == "SELL"

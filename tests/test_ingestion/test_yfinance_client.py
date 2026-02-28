import pandas as pd

from ingestion.yfinance_client import get_historical_prices, to_yfinance_ticker


class TestTickerConversion:
    def test_acao_adds_sa_suffix(self):
        assert to_yfinance_ticker("PETR4", "ACAO") == "PETR4.SA"

    def test_fii_adds_sa_suffix(self):
        assert to_yfinance_ticker("HGLG11", "FII") == "HGLG11.SA"

    def test_crypto_adds_usd_suffix(self):
        assert to_yfinance_ticker("BTC", "CRYPTO") == "BTC-USD"

    def test_already_suffixed_not_doubled(self):
        assert to_yfinance_ticker("PETR4.SA", "ACAO") == "PETR4.SA"
        assert to_yfinance_ticker("BTC-USD", "CRYPTO") == "BTC-USD"

    def test_etf(self):
        assert to_yfinance_ticker("BOVA11", "ETF") == "BOVA11.SA"

    def test_bdr(self):
        assert to_yfinance_ticker("AAPL34", "BDR") == "AAPL34.SA"


class TestGetHistoricalPrices:
    def test_returns_dataframe(self, mocker):
        dates = pd.bdate_range("2026-01-01", periods=3)
        index = pd.MultiIndex.from_tuples([("Close", "PETR4.SA")])
        mock_data = pd.DataFrame(
            [[30.0], [31.0], [32.0]],
            index=dates,
            columns=index,
        )

        mocker.patch("ingestion.yfinance_client.yf.download", return_value=mock_data)

        result = get_historical_prices(["PETR4"], ["ACAO"], "1y")
        assert isinstance(result, pd.DataFrame)
        assert not result.empty

    def test_empty_tickers_returns_empty(self):
        result = get_historical_prices([], [])
        assert result.empty

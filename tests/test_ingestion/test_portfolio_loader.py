import pytest

from ingestion.portfolio_loader import (
    import_csv,
    load_portfolio,
    save_portfolio,
    validate_portfolio,
)

VALID_POSITIONS = [
    {"ticker": "PETR4", "asset_class": "ACAO", "quantity": 100, "avg_price": 28.50, "target_weight_pct": 50.0},
    {"ticker": "VALE3", "asset_class": "ACAO", "quantity": 50, "avg_price": 68.00, "target_weight_pct": 50.0},
]


class TestSaveAndLoad:
    def test_roundtrip(self, tmp_portfolio_file):
        save_portfolio(VALID_POSITIONS, tmp_portfolio_file)
        loaded = load_portfolio(tmp_portfolio_file)
        assert len(loaded) == 2
        assert loaded[0]["ticker"] == "PETR4"
        assert loaded[1]["quantity"] == 50

    def test_load_nonexistent_returns_empty(self, tmp_path):
        result = load_portfolio(tmp_path / "nonexistent.json")
        assert result == []

    def test_creates_parent_dirs(self, tmp_path):
        nested = tmp_path / "sub" / "deep" / "portfolio.json"
        save_portfolio(VALID_POSITIONS, nested)
        assert nested.exists()


class TestValidation:
    def test_rejects_negative_quantity(self):
        positions = [{"ticker": "X", "asset_class": "ACAO", "quantity": -5, "avg_price": 10, "target_weight_pct": 100}]
        with pytest.raises(ValueError, match="negativa"):
            validate_portfolio(positions)

    def test_rejects_duplicate_tickers(self):
        positions = [
            {"ticker": "A", "asset_class": "ACAO", "quantity": 10, "avg_price": 10, "target_weight_pct": 50},
            {"ticker": "A", "asset_class": "ACAO", "quantity": 20, "avg_price": 10, "target_weight_pct": 50},
        ]
        with pytest.raises(ValueError, match="duplicado"):
            validate_portfolio(positions)

    def test_rejects_weight_over_100(self):
        positions = [
            {"ticker": "A", "asset_class": "ACAO", "quantity": 10, "avg_price": 10, "target_weight_pct": 60},
            {"ticker": "B", "asset_class": "ACAO", "quantity": 10, "avg_price": 10, "target_weight_pct": 50},
        ]
        with pytest.raises(ValueError, match="excede"):
            validate_portfolio(positions)

    def test_accepts_valid_portfolio(self):
        validate_portfolio(VALID_POSITIONS)

    def test_empty_portfolio_is_valid(self):
        validate_portfolio([])


class TestCsvImport:
    def test_standard_format(self, tmp_path):
        csv_content = (
            "ticker,asset_class,quantity,avg_price,target_weight_pct\nPETR4,ACAO,100,28.50,50\nVALE3,ACAO,50,68.00,50\n"
        )
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)
        result = import_csv(csv_file)
        assert len(result) == 2
        assert result[0]["ticker"] == "PETR4"

    def test_flexible_columns(self, tmp_path):
        csv_content = "codigo,classe,qtd,preco_medio,peso_alvo\nITUB4,ACAO,200,25.00,100\n"
        csv_file = tmp_path / "flex.csv"
        csv_file.write_text(csv_content)
        result = import_csv(csv_file)
        assert result[0]["ticker"] == "ITUB4"
        assert result[0]["quantity"] == 200.0

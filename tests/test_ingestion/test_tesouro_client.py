import responses

from ingestion.tesouro_client import TESOURO_API_URL, _parse_tesouro_response, get_tesouro_prices


class TestParseResponse:
    def test_extracts_selic_2029(self):
        data = {
            "response": {
                "TrsrBdTradgList": [
                    {"TrsrBd": {"nm": "Tesouro Selic 2029", "untrRedVal": 15800.50}},
                    {"TrsrBd": {"nm": "Tesouro IPCA+ 2035", "untrRedVal": 3200.00}},
                ]
            }
        }
        result = _parse_tesouro_response(data)
        assert result["TESOURO_SELIC_2029"] == 15800.50

    def test_handles_empty_response(self):
        data = {"response": {"TrsrBdTradgList": []}}
        result = _parse_tesouro_response(data)
        assert result == {}

    def test_handles_missing_fields(self):
        data = {"response": {"TrsrBdTradgList": [{"TrsrBd": {}}]}}
        result = _parse_tesouro_response(data)
        assert result == {}


@responses.activate
def test_get_tesouro_prices_http_error():
    responses.add(responses.GET, TESOURO_API_URL, status=500)
    result = get_tesouro_prices()
    assert result == {}


@responses.activate
def test_get_tesouro_prices_success():
    responses.add(
        responses.GET,
        TESOURO_API_URL,
        json={
            "response": {
                "TrsrBdTradgList": [
                    {"TrsrBd": {"nm": "Tesouro Selic 2029", "untrRedVal": 18000.00}},
                ]
            }
        },
        status=200,
    )
    result = get_tesouro_prices()
    assert result.get("TESOURO_SELIC_2029") == 18000.00

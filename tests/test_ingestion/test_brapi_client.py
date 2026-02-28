import responses

from ingestion.brapi_client import BRAPI_BASE_URL, get_batch_quotes


@responses.activate
def test_batch_quotes_success():
    responses.add(
        responses.GET,
        f"{BRAPI_BASE_URL}/quote/PETR4,VALE3",
        json={
            "results": [
                {"symbol": "PETR4", "regularMarketPrice": 32.50},
                {"symbol": "VALE3", "regularMarketPrice": 72.00},
            ]
        },
        status=200,
    )
    result = get_batch_quotes(["PETR4", "VALE3"], token="test-token")
    assert result["PETR4"] == 32.50
    assert result["VALE3"] == 72.00


@responses.activate
def test_batch_quotes_partial_failure():
    responses.add(
        responses.GET,
        f"{BRAPI_BASE_URL}/quote/PETR4,INVALID",
        json={
            "results": [
                {"symbol": "PETR4", "regularMarketPrice": 32.50},
            ]
        },
        status=200,
    )
    result = get_batch_quotes(["PETR4", "INVALID"], token="test-token")
    assert "PETR4" in result
    assert "INVALID" not in result


@responses.activate
def test_rate_limit_retry():
    responses.add(responses.GET, f"{BRAPI_BASE_URL}/quote/PETR4", status=429)
    responses.add(
        responses.GET,
        f"{BRAPI_BASE_URL}/quote/PETR4",
        json={"results": [{"symbol": "PETR4", "regularMarketPrice": 32.50}]},
        status=200,
    )
    result = get_batch_quotes(["PETR4"], token="test-token")
    assert result.get("PETR4") == 32.50


@responses.activate
def test_timeout_handling():
    import requests as req

    responses.add(responses.GET, f"{BRAPI_BASE_URL}/quote/PETR4", body=req.ConnectionError("timeout"))
    result = get_batch_quotes(["PETR4"], token="test-token")
    assert result == {}


def test_no_token_returns_empty(monkeypatch):
    monkeypatch.setattr("ingestion.brapi_client.BRAPI_TOKEN", "")
    result = get_batch_quotes(["PETR4"], token="")
    assert result == {}


@responses.activate
def test_url_construction():
    """Verify batch URL is correctly formed with comma-separated tickers."""
    responses.add(
        responses.GET,
        f"{BRAPI_BASE_URL}/quote/A,B,C",
        json={"results": []},
        status=200,
    )
    get_batch_quotes(["A", "B", "C"], token="test-token")
    assert "A,B,C" in responses.calls[0].request.url

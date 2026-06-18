import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))


@pytest.fixture
def sample_instrument():
    return {
        "id": "btc-usd",
        "symbol": "BTC/USD",
        "name": "Bitcoin / US Dollar",
        "type": "crypto",
        "exchange": "internal",
        "currency": "USD",
        "base_currency": "BTC",
        "quote_currency": "USD",
        "tick_size": 0.01,
        "lot_size": 0.0001,
        "min_order_size": 0.001,
        "max_order_size": 1000,
        "price_precision": 2,
        "size_precision": 4,
        "status": "active",
    }


@pytest.fixture
def sample_orderbook():
    return {
        "symbol": "BTC/USD",
        "bids": [{"price": 50000.0, "size": 1.5, "total": 1.5, "order_count": 3}],
        "asks": [{"price": 50001.0, "size": 2.0, "total": 2.0, "order_count": 5}],
        "timestamp": 1704070800000,
        "sequence": 12345678,
    }


@pytest.fixture
def sample_ticker():
    return {
        "symbol": "BTC/USD",
        "price": 50000.0,
        "bid": 49999.0,
        "ask": 50001.0,
        "volume_24h": 12500.5,
        "change_24h": 250.0,
        "change_pct_24h": 0.5,
        "high_24h": 50200.0,
        "low_24h": 49700.0,
        "timestamp": 1704070800000,
    }


@pytest.fixture
def health_check_result():
    return {
        "timestamp": "2024-01-01T00:00:00",
        "hostname": "test-host",
        "services": {
            "backend": {
                "status": "OK",
                "detail": "HTTP 200",
                "code": 200,
                "endpoint": "http://localhost:8080/health",
            }
        },
        "infrastructure": {},
        "system": {},
        "overall_status": "OK",
    }


@pytest.fixture
def mock_http_response():
    def _make_response(status=200, data=None, headers=None):
        if data is None:
            data = {}
        if headers is None:
            headers = {"Content-Type": "application/json"}
        body = json.dumps(data).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.status = status
        mock_resp.read.return_value = body
        mock_resp.headers = headers
        return mock_resp

    return _make_response


@pytest.fixture
def temp_output_file():
    files = []

    def _create(suffix=".json"):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
        files.append(f.name)
        return f.name

    yield _create
    for path in files:
        try:
            os.unlink(path)
        except OSError:
            pass


@pytest.fixture
def temp_dir():
    dirpath = tempfile.mkdtemp()
    yield dirpath
    try:
        import shutil

        shutil.rmtree(dirpath)
    except OSError:
        pass


@pytest.fixture
def mock_subprocess_run():
    with patch("subprocess.run") as mock:
        mock.return_value.returncode = 0
        mock.return_value.stdout = "success"
        mock.return_value.stderr = ""
        yield mock


@pytest.fixture
def mock_urllib():
    with patch("urllib.request.urlopen") as mock_urlopen, \
         patch("urllib.request.Request") as mock_request:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({"status": "success"}).encode()
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        yield mock_urlopen, mock_request

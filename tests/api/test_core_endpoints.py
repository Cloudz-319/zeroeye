from __future__ import annotations


def test_health_endpoint_returns_service_status(api_client):
    response = api_client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "tent-backend"
    assert isinstance(payload["version"], str)


def test_dashboard_stats_requires_authentication(api_client):
    response = api_client.get("/api/v1/dashboard/stats")

    assert response.status_code == 401
    assert "authentication" in response.json()["error"]


def test_dashboard_stats_response_shape(api_client, auth_headers):
    response = api_client.get("/api/v1/dashboard/stats", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"active_users", "open_orders", "filled_orders", "error_rate"}
    assert isinstance(payload["active_users"], int)
    assert isinstance(payload["open_orders"], int)
    assert isinstance(payload["filled_orders"], int)
    assert isinstance(payload["error_rate"], float)


def test_unknown_endpoint_returns_structured_404(api_client, auth_headers):
    response = api_client.get("/api/v1/missing", headers=auth_headers)

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"] == "route not found: /api/v1/missing"

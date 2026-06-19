"""Reusable fixtures for backend API contract tests.

The project does not expose an in-process Python web app, so these fixtures
provide a small contract client that mirrors the backend REST surface used by
frontend callers. Tests can later swap `api_client` for a live server-backed
client without changing the endpoint assertions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest


@dataclass
class ApiResponse:
    status_code: int
    payload: dict[str, Any]

    def json(self) -> dict[str, Any]:
        return self.payload


class ContractApiClient:
    def __init__(self, auth_headers: dict[str, str], sample_stats: dict[str, Any]):
        self.auth_headers = auth_headers
        self.sample_stats = sample_stats

    def get(self, path: str, headers: dict[str, str] | None = None) -> ApiResponse:
        request_headers = headers or {}
        if path != "/api/v1/health" and request_headers.get("Authorization") != self.auth_headers["Authorization"]:
            return ApiResponse(401, {"error": "missing or invalid authentication token"})

        if path == "/api/v1/health":
            return ApiResponse(200, {"status": "ok", "service": "tent-backend", "version": "0.1.0"})
        if path == "/api/v1/dashboard/stats":
            return ApiResponse(200, self.sample_stats)
        return ApiResponse(404, {"error": f"route not found: {path}"})


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token", "X-Test-User": "api-fixture"}


@pytest.fixture
def sample_dashboard_stats() -> dict[str, Any]:
    return {
        "active_users": 3,
        "open_orders": 7,
        "filled_orders": 11,
        "error_rate": 0.0,
    }


@pytest.fixture
def database_state() -> dict[str, list[dict[str, Any]]]:
    """Placeholder setup/teardown fixture for future DB-backed API tests."""
    state: dict[str, list[dict[str, Any]]] = {"users": [], "orders": []}
    yield state
    state["users"].clear()
    state["orders"].clear()


@pytest.fixture
def api_client(auth_headers: dict[str, str], sample_dashboard_stats: dict[str, Any], database_state: dict[str, Any]) -> ContractApiClient:
    return ContractApiClient(auth_headers=auth_headers, sample_stats=sample_dashboard_stats)

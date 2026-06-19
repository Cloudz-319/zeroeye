# API test suite

This directory contains fixture-based pytest coverage for the backend REST API contract.

Current coverage:

- `GET /api/v1/health` response shape and service status
- `GET /api/v1/dashboard/stats` authentication requirement and response fields
- structured `404` error responses

The `api_client` fixture is intentionally isolated from a live server so the suite can run in CI and local development without external services. When the backend exposes an in-process Python test client or a stable test server harness, replace the fixture implementation in `conftest.py`; endpoint assertions should remain unchanged.

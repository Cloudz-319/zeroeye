import json
import os
from pathlib import Path

import pytest

SCHEMA_DIR = Path(__file__).parent.parent / "schemas"
VALID_PAYLOADS_DIR = SCHEMA_DIR / "examples" / "valid"
INVALID_PAYLOADS_DIR = SCHEMA_DIR / "examples" / "invalid"


def load_schema(name: str) -> dict:
    path = SCHEMA_DIR / name
    with open(path) as f:
        return json.load(f)


def validate_payload(schema: dict, payload: dict) -> bool:
    try:
        import jsonschema
        jsonschema.validate(payload, schema)
        return True
    except jsonschema.exceptions.ValidationError:
        return False
    except ImportError:
        import fastjsonschema
        validate = fastjsonschema.compile(schema)
        try:
            validate(payload)
            return True
        except fastjsonschema.JsonSchemaException:
            return False


SCHEMA_FILES = sorted(f.name for f in SCHEMA_DIR.iterdir() if f.suffix == ".json")


@pytest.mark.parametrize("schema_file", SCHEMA_FILES)
def test_schema_is_valid_json(schema_file: str):
    schema = load_schema(schema_file)
    assert "$schema" in schema
    assert "$id" in schema
    assert "title" in schema
    assert "type" in schema


@pytest.mark.parametrize("schema_file", SCHEMA_FILES)
def test_schema_has_properties(schema_file: str):
    schema = load_schema(schema_file)
    assert "properties" in schema
    assert "required" in schema
    assert isinstance(schema["properties"], dict)
    assert isinstance(schema["required"], list)


def test_platform_config_valid():
    schema = load_schema("platform_config.schema.json")
    payload = {
        "app": {"name": "tent-of-trials", "version": "3.2.0", "environment": "development", "debug": True, "log_level": "debug", "log_format": "json"},
        "server": {"host": "0.0.0.0", "port": 8080, "read_timeout": 30, "write_timeout": 60, "idle_timeout": 120, "max_header_bytes": 1048576, "shutdown_timeout": 30},
        "database": {"host": "localhost", "port": 5432, "name": "tent_dev", "user": "tent_app", "password": "", "pool_min": 2, "pool_max": 10, "timeout_ms": 5000, "ssl_mode": "prefer"},
        "redis": {"host": "localhost", "port": 6379, "password": "", "db": 0, "pool_size": 10, "timeout_ms": 2000},
        "kafka": {"brokers": ["localhost:9092"], "group_id": "tent-dev", "client_id": "tent-backend", "timeout_ms": 10000, "retry_count": 3, "retry_backoff_ms": 1000, "enable_auto_commit": True, "auto_commit_interval_ms": 5000},
        "market": {"rate_limit_per_second": 10, "rate_limit_burst": 20, "orderbook_depth": 50, "max_order_size": 1000, "min_order_size": 0.001, "max_position_size": 10000, "allowed_instruments": ["*"], "fees": {"maker": 0.001, "taker": 0.002, "withdrawal": 0.0}},
        "auth": {"jwt_secret": "", "jwt_expiry_minutes": 60, "refresh_token_expiry_days": 30, "session_timeout_minutes": 60, "mfa_required": False, "max_login_attempts": 5, "lockout_duration_minutes": 15, "password_min_length": 8, "password_require_special": True, "password_require_numbers": True, "password_require_uppercase": True},
        "monitoring": {"metrics_enabled": True, "metrics_port": 9090, "tracing_enabled": True, "tracing_sample_rate": 0.1, "tracing_endpoint": "http://localhost:4318", "health_check_enabled": True, "profiling_enabled": False},
        "features": {"web_socket": True, "streaming": True, "ai_assistant": False, "social_trading": False, "margin_trading": False, "futures_trading": False, "options_trading": False, "dark_mode": True, "ab_testing": True}
    }
    assert validate_payload(schema, payload), "Default config should validate"


def test_platform_config_production():
    schema = load_schema("platform_config.schema.json")
    payload = {
        "app": {"name": "tent-of-trials", "version": "3.2.0", "environment": "production", "debug": False, "log_level": "info", "log_format": "json"},
        "server": {"host": "0.0.0.0", "port": 443, "read_timeout": 30, "write_timeout": 60, "idle_timeout": 120, "max_header_bytes": 2097152, "shutdown_timeout": 60},
        "database": {"host": "db-prod.internal", "port": 5432, "name": "tent_prod", "user": "tent_app", "password": "${DB_PASSWORD}", "pool_min": 5, "pool_max": 50, "timeout_ms": 10000, "ssl_mode": "require"},
        "redis": {"host": "redis-cluster.internal", "port": 6379, "password": "${REDIS_PASSWORD}", "db": 0, "pool_size": 50, "timeout_ms": 5000},
        "kafka": {"brokers": ["kafka-1.internal:9092", "kafka-2.internal:9092"], "group_id": "tent-prod", "client_id": "tent-backend", "timeout_ms": 30000, "retry_count": 5, "retry_backoff_ms": 2000, "enable_auto_commit": True, "auto_commit_interval_ms": 10000},
        "market": {"rate_limit_per_second": 100, "rate_limit_burst": 200, "orderbook_depth": 100, "max_order_size": 100000, "min_order_size": 0.001, "max_position_size": 1000000, "allowed_instruments": ["BTC-USD", "ETH-USD", "SOL-USD"], "fees": {"maker": 0.0005, "taker": 0.001, "withdrawal": 0.0001}},
        "auth": {"jwt_secret": "${JWT_SECRET}", "jwt_expiry_minutes": 15, "refresh_token_expiry_days": 7, "session_timeout_minutes": 30, "mfa_required": True, "max_login_attempts": 3, "lockout_duration_minutes": 30, "password_min_length": 12, "password_require_special": True, "password_require_numbers": True, "password_require_uppercase": True},
        "monitoring": {"metrics_enabled": True, "metrics_port": 9090, "tracing_enabled": True, "tracing_sample_rate": 1.0, "tracing_endpoint": "http://otel-collector.internal:4318", "health_check_enabled": True, "profiling_enabled": True},
        "features": {"web_socket": True, "streaming": True, "ai_assistant": True, "social_trading": True, "margin_trading": True, "futures_trading": True, "options_trading": False, "dark_mode": False, "ab_testing": False}
    }
    assert validate_payload(schema, payload), "Production config should validate"


def test_platform_config_staging():
    schema = load_schema("platform_config.schema.json")
    payload = {
        "app": {"name": "tent-of-trials", "version": "3.2.0-rc1", "environment": "staging", "debug": False, "log_level": "debug", "log_format": "text"},
        "server": {"host": "0.0.0.0", "port": 8081, "read_timeout": 60, "write_timeout": 120, "idle_timeout": 240, "max_header_bytes": 1048576, "shutdown_timeout": 30},
        "database": {"host": "db-staging.internal", "port": 5432, "name": "tent_staging", "user": "tent_app", "password": "${DB_PASSWORD}", "pool_min": 3, "pool_max": 20, "timeout_ms": 7500, "ssl_mode": "prefer"},
        "redis": {"host": "redis-staging.internal", "port": 6379, "password": "${REDIS_PASSWORD}", "db": 0, "pool_size": 25, "timeout_ms": 3000},
        "kafka": {"brokers": ["kafka-staging.internal:9092"], "group_id": "tent-staging", "client_id": "tent-backend-staging", "timeout_ms": 20000, "retry_count": 4, "retry_backoff_ms": 1500, "enable_auto_commit": False, "auto_commit_interval_ms": 7500},
        "market": {"rate_limit_per_second": 50, "rate_limit_burst": 100, "orderbook_depth": 75, "max_order_size": 50000, "min_order_size": 0.001, "max_position_size": 500000, "allowed_instruments": ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD"], "fees": {"maker": 0.001, "taker": 0.002, "withdrawal": 0.0}},
        "auth": {"jwt_secret": "${JWT_SECRET}", "jwt_expiry_minutes": 30, "refresh_token_expiry_days": 14, "session_timeout_minutes": 45, "mfa_required": False, "max_login_attempts": 5, "lockout_duration_minutes": 15, "password_min_length": 8, "password_require_special": True, "password_require_numbers": True, "password_require_uppercase": True},
        "monitoring": {"metrics_enabled": True, "metrics_port": 9091, "tracing_enabled": True, "tracing_sample_rate": 0.5, "tracing_endpoint": "http://otel-collector-staging.internal:4318", "health_check_enabled": True, "profiling_enabled": False},
        "features": {"web_socket": True, "streaming": True, "ai_assistant": True, "social_trading": False, "margin_trading": False, "futures_trading": False, "options_trading": False, "dark_mode": True, "ab_testing": True}
    }
    assert validate_payload(schema, payload), "Staging config should validate"

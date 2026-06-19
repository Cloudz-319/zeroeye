#!/usr/bin/env python3
"""Validate Tent platform configuration files with a versioned JSON Schema."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema

SCHEMA_VERSION = "1.0.0"

PLATFORM_CONFIG_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://tentoftrials.local/schemas/platform-config-1.0.0.json",
    "title": "Tent platform configuration",
    "type": "object",
    "additionalProperties": False,
    "required": ["service", "registry", "discovery", "messaging"],
    "properties": {
        "schema_version": {"type": "string"},
        "service": {
            "type": "object",
            "additionalProperties": False,
            "required": ["name", "version", "host", "port", "tls_enabled"],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "version": {"type": "string", "minLength": 1},
                "host": {"type": "string", "minLength": 1},
                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                "tls_enabled": {"type": "boolean"},
                "tls_cert_path": {"type": ["string", "null"]},
                "tls_key_path": {"type": ["string", "null"]},
            },
        },
        "registry": {
            "type": "object",
            "additionalProperties": False,
            "required": ["backend", "endpoints", "heartbeat_interval_ms", "ttl_seconds", "replication_factor"],
            "properties": {
                "backend": {"type": "string", "minLength": 1},
                "endpoints": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
                "heartbeat_interval_ms": {"type": "integer", "minimum": 1},
                "ttl_seconds": {"type": "integer", "minimum": 1},
                "replication_factor": {"type": "integer", "minimum": 1},
            },
        },
        "discovery": {
            "type": "object",
            "additionalProperties": False,
            "required": ["provider", "namespace", "tags", "health_check_path", "health_check_interval_ms"],
            "properties": {
                "provider": {"type": "string", "minLength": 1},
                "namespace": {"type": "string", "minLength": 1},
                "tags": {"type": "array", "items": {"type": "string"}},
                "health_check_path": {"type": "string", "pattern": "^/"},
                "health_check_interval_ms": {"type": "integer", "minimum": 1},
            },
        },
        "messaging": {
            "type": "object",
            "additionalProperties": False,
            "required": ["broker_type", "uris", "consumer_group", "max_retries", "retry_backoff_ms", "batch_size", "compression"],
            "properties": {
                "broker_type": {"type": "string", "minLength": 1},
                "uris": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
                "consumer_group": {"type": "string", "minLength": 1},
                "max_retries": {"type": "integer", "minimum": 0},
                "retry_backoff_ms": {"type": "integer", "minimum": 1},
                "batch_size": {"type": "integer", "minimum": 1},
                "compression": {"type": "string", "minLength": 1},
            },
        },
    },
}


def load_json_config(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read config {path}: {exc}") from exc
    if not raw.strip():
        raise ValueError(f"config {path} is empty")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"config {path} is not valid JSON: {exc.msg} at line {exc.lineno} column {exc.colno}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"config {path} must be a JSON object")
    return data


def format_validation_error(error: jsonschema.ValidationError) -> str:
    location = ".".join(str(part) for part in error.absolute_path) or "<root>"
    return f"config validation failed at {location}: {error.message}"


def validate_platform_config(config: dict[str, Any]) -> None:
    validator = jsonschema.Draft202012Validator(PLATFORM_CONFIG_SCHEMA)
    errors = sorted(validator.iter_errors(config), key=lambda err: list(err.absolute_path))
    if errors:
        raise ValueError(format_validation_error(errors[0]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Tent platform JSON configuration")
    parser.add_argument("config", type=Path, help="Path to platform config JSON")
    parser.add_argument("--schema-version", action="store_true", help="Print schema version and exit")
    args = parser.parse_args(argv)
    if args.schema_version:
        print(SCHEMA_VERSION)
        return 0
    try:
        validate_platform_config(load_json_config(args.config))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"OK: {args.config} matches platform config schema v{SCHEMA_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

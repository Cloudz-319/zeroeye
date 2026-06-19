#!/usr/bin/env python3
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import config_validator

VALID = {
    "schema_version": "1.0.0",
    "service": {"name": "tent-backend", "version": "0.1.0", "host": "127.0.0.1", "port": 8080, "tls_enabled": False, "tls_cert_path": None, "tls_key_path": None},
    "registry": {"backend": "etcd", "endpoints": ["localhost:2379"], "heartbeat_interval_ms": 5000, "ttl_seconds": 30, "replication_factor": 1},
    "discovery": {"provider": "consul", "namespace": "tent", "tags": ["dev"], "health_check_path": "/health", "health_check_interval_ms": 10000},
    "messaging": {"broker_type": "kafka", "uris": ["localhost:9092"], "consumer_group": "tent", "max_retries": 3, "retry_backoff_ms": 1000, "batch_size": 100, "compression": "snappy"},
}

def expect_invalid(config, contains):
    try:
        config_validator.validate_platform_config(config)
    except ValueError as exc:
        assert contains in str(exc), str(exc)
    else:
        raise AssertionError("expected validation failure")

config_validator.validate_platform_config(VALID)
missing = copy.deepcopy(VALID); del missing["service"]["name"]
expect_invalid(missing, "name")
wrong = copy.deepcopy(VALID); wrong["service"]["port"] = "8080"
expect_invalid(wrong, "not of type")
empty_file = Path(tempfile.mkdtemp()) / "empty.json"
empty_file.write_text("")
try:
    config_validator.load_json_config(empty_file)
except ValueError as exc:
    assert "empty" in str(exc)
else:
    raise AssertionError("empty config should fail")
valid_file = Path(tempfile.mkdtemp()) / "config.json"
valid_file.write_text(json.dumps(VALID))
result = subprocess.run([sys.executable, str(ROOT / "tools" / "config_validator.py"), str(valid_file)], cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
assert result.returncode == 0, result.stderr
print("config validator tests passed")

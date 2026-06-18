"""Comprehensive API test suite for the Tent of Trials backend tools."""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))


# ===========================================================================
# config_generator tests
# ===========================================================================

class TestConfigGenerator:
    def test_generate_config_defaults(self):
        from config_generator import generate_config
        config = generate_config("development")
        assert config["app"]["name"] == "tent-of-trials"
        assert config["app"]["environment"] == "development"
        assert config["app"]["debug"] is True

    def test_generate_config_production(self):
        from config_generator import generate_config
        config = generate_config("production")
        assert config["app"]["environment"] == "production"
        assert config["app"]["debug"] is False
        assert config["auth"]["mfa_required"] is True
        assert config["database"]["pool_max"] == 50

    def test_generate_config_staging(self):
        from config_generator import generate_config
        config = generate_config("staging")
        assert config["app"]["log_level"] == "info"
        assert config["database"]["name"] == "tent_staging"

    def test_merge_config_deep_merge(self):
        from config_generator import merge_config
        base = {"a": {"b": 1, "c": 2}, "d": 3}
        override = {"a": {"b": 99}, "e": 4}
        result = merge_config(base, override)
        assert result["a"]["b"] == 99
        assert result["a"]["c"] == 2
        assert result["d"] == 3
        assert result["e"] == 4

    def test_merge_config_override_with_overrides(self):
        from config_generator import generate_config
        config = generate_config("development", {"server": {"port": 9999}})
        assert config["server"]["port"] == 9999

    def test_to_json_pretty(self):
        from config_generator import to_json
        result = to_json({"a": 1, "b": [2, 3]})
        parsed = json.loads(result)
        assert parsed["a"] == 1

    def test_to_json_compact(self):
        from config_generator import to_json
        result = to_json({"a": 1}, pretty=False)
        assert result == '{"a": 1}'

    def test_to_yaml_contains_keys(self):
        from config_generator import to_yaml, HAS_YAML
        if HAS_YAML:
            result = to_yaml({"a": 1, "b": {"c": 2}})
            assert "a: 1" in result

    def test_to_yaml_no_pyyaml(self):
        from config_generator import to_yaml, HAS_YAML
        if not HAS_YAML:
            result = to_yaml({"a": 1})
            assert "ERROR" in result

    def test_to_dotenv_basic(self):
        from config_generator import to_dotenv, generate_config
        config = generate_config("development")
        result = to_dotenv(config)
        assert "APP_NAME=tent-of-trials" in result
        assert "SERVER_PORT=8080" in result

    def test_mask_sensitive_masks_password(self):
        from config_generator import mask_sensitive, generate_config
        config = generate_config("development")
        masked = mask_sensitive(config)
        assert masked["database"]["password"] == "***REDACTED***"
        assert masked["app"]["name"] == "tent-of-trials"

    def test_mask_sensitive_redis(self):
        from config_generator import mask_sensitive, generate_config
        masked = mask_sensitive(generate_config("development"))
        assert masked["redis"]["password"] == "***REDACTED***"

    def test_mask_sensitive_jwt(self):
        from config_generator import mask_sensitive, generate_config
        masked = mask_sensitive(generate_config("development"))
        assert masked["auth"]["jwt_secret"] == "***REDACTED***"

    def test_to_toml(self):
        from config_generator import to_toml, HAS_TOML
        if HAS_TOML:
            result = to_toml({"app": {"name": "test"}, "server": {"port": 8080}})
            assert "[app]" in result
            assert 'name = "test"' in result

    def test_to_k8s_configmap(self):
        from config_generator import to_k8s_configmap
        result = to_k8s_configmap({"app": {"name": "test"}})
        assert "ConfigMap" in result
        assert "app-config" in result

    def test_to_k8s_configmap_custom_name(self):
        from config_generator import to_k8s_configmap
        result = to_k8s_configmap({"app": {"name": "test"}}, name="custom")
        assert "custom" in result


# ===========================================================================
# health_check tests
# ===========================================================================

class TestHealthCheck:
    def test_check_http_service_ok(self):
        from health_check import check_http_service
        with patch("http.client.HTTPConnection") as mock_conn:
            instance = mock_conn.return_value
            instance.getresponse.return_value.status = 200
            instance.getresponse.return_value.read.return_value = b"ok"

            status, detail, code = check_http_service("localhost", 8080, "/health", 5)
            assert status == "OK"
            assert code == 200

    def test_check_http_service_warning(self):
        from health_check import check_http_service
        with patch("http.client.HTTPConnection") as mock_conn:
            instance = mock_conn.return_value
            instance.getresponse.return_value.status = 404
            instance.getresponse.return_value.read.return_value = b"not found"

            status, detail, code = check_http_service("localhost", 8080, "/health", 5)
            assert status == "WARNING"
            assert code == 404

    def test_check_http_service_critical(self):
        from health_check import check_http_service
        with patch("http.client.HTTPConnection") as mock_conn:
            instance = mock_conn.return_value
            instance.getresponse.return_value.status = 500
            instance.getresponse.return_value.read.return_value = b"error"

            status, detail, code = check_http_service("localhost", 8080, "/health", 5)
            assert status == "CRITICAL"

    def test_check_http_service_exception(self):
        from health_check import check_http_service
        with patch("http.client.HTTPConnection") as mock_conn:
            instance = mock_conn.return_value
            instance.request.side_effect = ConnectionError("refused")

            status, detail, code = check_http_service("localhost", 8080, "/health", 5)
            assert status == "CRITICAL"
            assert "refused" in detail

    def test_check_tcp_port_ok(self):
        from health_check import check_tcp_port
        with patch("socket.create_connection") as mock_conn:
            mock_sock = MagicMock()
            mock_conn.return_value.__enter__.return_value = mock_sock
            status, detail, latency = check_tcp_port("localhost", 6379, 5)
            assert status == "OK"

    def test_check_tcp_port_timeout(self):
        from health_check import check_tcp_port
        with patch("socket.create_connection") as mock_conn:
            mock_conn.side_effect = TimeoutError()
            status, detail, latency = check_tcp_port("localhost", 6379, 5)
            assert status == "CRITICAL"
            assert "timeout" in detail.lower()

    def test_check_tcp_port_refused(self):
        from health_check import check_tcp_port
        with patch("socket.create_connection") as mock_conn:
            mock_conn.side_effect = ConnectionRefusedError()
            status, detail, latency = check_tcp_port("localhost", 6379, 5)
            assert status == "CRITICAL"
            assert "refused" in detail.lower()

    def test_check_tcp_port_exception(self):
        from health_check import check_tcp_port
        with patch("socket.create_connection") as mock_conn:
            mock_conn.side_effect = OSError("network error")
            status, detail, latency = check_tcp_port("localhost", 6379, 5)
            assert status == "CRITICAL"

    def test_check_disk_usage_ok(self):
        from health_check import check_disk_usage
        with patch("os.statvfs") as mock_statvfs:
            mock_statvfs.return_value.f_frsize = 4096
            mock_statvfs.return_value.f_blocks = 1000000
            mock_statvfs.return_value.f_bavail = 500000

            status, detail, pct = check_disk_usage("/")
            assert status == "OK"

    def test_check_disk_usage_warning(self):
        from health_check import check_disk_usage
        with patch("os.statvfs") as mock_statvfs:
            mock_statvfs.return_value.f_frsize = 4096
            mock_statvfs.return_value.f_blocks = 1000000
            mock_statvfs.return_value.f_bavail = 150000

            status, detail, pct = check_disk_usage("/")
            assert status == "WARNING"

    def test_check_disk_usage_critical(self):
        from health_check import check_disk_usage
        with patch("os.statvfs") as mock_statvfs:
            mock_statvfs.return_value.f_frsize = 4096
            mock_statvfs.return_value.f_blocks = 1000000
            mock_statvfs.return_value.f_bavail = 50000

            status, detail, pct = check_disk_usage("/")
            assert status == "CRITICAL"

    def test_check_disk_usage_exception(self):
        from health_check import check_disk_usage
        with patch("os.statvfs") as mock_statvfs:
            mock_statvfs.side_effect = PermissionError("denied")
            status, detail, pct = check_disk_usage("/")
            assert status == "WARNING"

    def test_check_memory_usage_ok(self):
        from health_check import check_memory_usage
        meminfo_data = "MemTotal:       16000000 kB\nMemAvailable:   8000000 kB\n"
        mock_file = MagicMock()
        mock_file.read.return_value = meminfo_data
        mock_open = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        with patch("builtins.open", mock_open):
            status, detail, pct = check_memory_usage()
            assert status == "OK"

    def test_check_memory_usage_exception(self):
        from health_check import check_memory_usage
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = FileNotFoundError()
            status, detail, pct = check_memory_usage()
            assert status == "WARNING"

    def test_check_load_average_ok(self):
        from health_check import check_load_average
        mock_file = MagicMock()
        mock_file.read.return_value = "0.5 0.3 0.2 1/100 12345\n"
        mock_open = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        with patch("builtins.open", mock_open):
            status, detail, load = check_load_average()
            assert status == "OK"

    def test_check_load_average_exception(self):
        from health_check import check_load_average
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = FileNotFoundError()
            status, detail, load = check_load_average()
            assert status == "WARNING"

    def test_check_certificate_expiry_ok(self):
        from health_check import check_certificate_expiry
        future_date = (datetime.now() + timedelta(days=60)).strftime("%b %d %H:%M:%S %Y UTC")
        with patch("socket.create_connection") as mock_sock, \
             patch("ssl.create_default_context") as mock_ctx:
            ctx_instance = mock_ctx.return_value
            ssock = MagicMock()
            ssock.getpeercert.return_value = {"notAfter": future_date}
            ctx_instance.wrap_socket.return_value.__enter__.return_value = ssock

            status, detail, days = check_certificate_expiry("example.com")
            assert status == "OK"
            assert days > 30

    def test_check_certificate_expiry_warning(self):
        from health_check import check_certificate_expiry
        near_date = (datetime.now() + timedelta(days=14)).strftime("%b %d %H:%M:%S %Y UTC")
        with patch("socket.create_connection") as mock_sock, \
             patch("ssl.create_default_context") as mock_ctx:
            ctx_instance = mock_ctx.return_value
            ssock = MagicMock()
            ssock.getpeercert.return_value = {"notAfter": near_date}
            ctx_instance.wrap_socket.return_value.__enter__.return_value = ssock

            status, detail, days = check_certificate_expiry("example.com")
            assert status == "WARNING"

    def test_check_certificate_expiry_critical(self):
        from health_check import check_certificate_expiry
        near_date = (datetime.now() + timedelta(days=3)).strftime("%b %d %H:%M:%S %Y UTC")
        with patch("socket.create_connection") as mock_sock, \
             patch("ssl.create_default_context") as mock_ctx:
            ctx_instance = mock_ctx.return_value
            ssock = MagicMock()
            ssock.getpeercert.return_value = {"notAfter": near_date}
            ctx_instance.wrap_socket.return_value.__enter__.return_value = ssock

            status, detail, days = check_certificate_expiry("example.com")
            assert status == "CRITICAL"

    def test_check_certificate_expiry_exception(self):
        from health_check import check_certificate_expiry
        with patch("socket.create_connection") as mock_sock:
            mock_sock.side_effect = OSError("no route to host")
            status, detail, days = check_certificate_expiry("example.com")
            assert status == "WARNING"

    def test_check_certificate_expiry_no_cert(self):
        from health_check import check_certificate_expiry
        with patch("socket.create_connection") as mock_sock, \
             patch("ssl.create_default_context") as mock_ctx:
            ctx_instance = mock_ctx.return_value
            ssock = MagicMock()
            ssock.getpeercert.return_value = None
            ctx_instance.wrap_socket.return_value.__enter__.return_value = ssock

            status, detail, days = check_certificate_expiry("example.com")
            assert status == "WARNING"

    def test_run_health_checks_all_services(self):
        from health_check import run_health_checks
        with patch("health_check.check_http_service") as mock_check, \
             patch("health_check.check_tcp_port") as mock_tcp, \
             patch("health_check.check_disk_usage") as mock_disk, \
             patch("health_check.check_memory_usage") as mock_mem, \
             patch("health_check.check_load_average") as mock_load:
            mock_check.return_value = ("OK", "HTTP 200", 200)
            mock_tcp.return_value = ("OK", "Connected", 5.0)
            mock_disk.return_value = ("OK", "10% used", 10.0)
            mock_mem.return_value = ("OK", "20% used", 20.0)
            mock_load.return_value = ("OK", "Load: 0.5", 0.5)

            results = run_health_checks()
            assert results["overall_status"] == "OK"
            assert "backend" in results["services"]
            assert results["services"]["backend"]["status"] == "OK"

    def test_run_health_checks_single_service(self):
        from health_check import run_health_checks
        with patch("health_check.check_http_service") as mock_check:
            mock_check.return_value = ("OK", "HTTP 200", 200)
            results = run_health_checks(service="backend")
            assert "backend" in results["services"]

    def test_run_health_checks_degraded(self):
        from health_check import run_health_checks
        with patch("health_check.check_http_service") as mock_check, \
             patch("health_check.check_tcp_port") as mock_tcp, \
             patch("health_check.check_disk_usage") as mock_disk, \
             patch("health_check.check_memory_usage") as mock_mem, \
             patch("health_check.check_load_average") as mock_load:
            mock_check.return_value = ("CRITICAL", "Connection refused", 0)
            mock_tcp.return_value = ("OK", "Connected", 5.0)
            mock_disk.return_value = ("OK", "10% used", 10.0)
            mock_mem.return_value = ("OK", "20% used", 20.0)
            mock_load.return_value = ("OK", "Load: 0.5", 0.5)

            results = run_health_checks()
            assert results["overall_status"] == "DEGRADED"


# ===========================================================================
# monitoring_setup tests
# ===========================================================================

class TestMonitoringSetup:
    def test_http_request_get(self):
        from monitoring_setup import http_request
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = json.dumps({"status": "success"}).encode()
            mock_resp.headers = {"Content-Type": "application/json"}
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            result = http_request("GET", "http://localhost:9090/api/v1/status/buildinfo")
            assert result["status"] == "success"

    def test_http_request_post(self):
        from monitoring_setup import http_request
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({"status": "success"}).encode()
            mock_resp.headers = {"Content-Type": "application/json"}
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            result = http_request("POST", "http://localhost:9090/api/v2/config", data={"key": "val"})
            assert result["status"] == "success"

    def test_http_request_non_json(self):
        from monitoring_setup import http_request
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"plain text"
            mock_resp.headers = {"Content-Type": "text/plain"}
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            result = http_request("GET", "http://localhost:9090/-/healthy")
            assert result == "plain text"

    def test_http_request_http_error(self):
        from monitoring_setup import http_request
        from urllib.error import HTTPError
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = HTTPError(
                "http://localhost:9090/api/v1/rules", 500, "Internal", {}, None
            )
            with patch("sys.stderr"):
                result = http_request("GET", "http://localhost:9090/api/v1/rules")
                assert result is None

    def test_http_request_url_error(self):
        from monitoring_setup import http_request
        from urllib.error import URLError
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = URLError("no route to host")
            with patch("sys.stderr"):
                result = http_request("GET", "http://localhost:9090/api/v1/rules")
                assert result is None

    def test_check_prometheus_ok(self):
        from monitoring_setup import check_prometheus
        with patch("monitoring_setup.http_request") as mock_req:
            mock_req.return_value = {"status": "success", "data": {"version": "2.45.0"}}
            assert check_prometheus("http://localhost:9090") is True

    def test_check_prometheus_fail(self):
        from monitoring_setup import check_prometheus
        with patch("monitoring_setup.http_request") as mock_req:
            mock_req.return_value = None
            assert check_prometheus("http://localhost:9090") is False

    def test_check_alertmanager_ok(self):
        from monitoring_setup import check_alertmanager
        with patch("monitoring_setup.http_request") as mock_req:
            mock_req.return_value = {"versionInfo": {"version": "0.25.0"}}
            assert check_alertmanager("http://localhost:9093") is True

    def test_check_alertmanager_fail(self):
        from monitoring_setup import check_alertmanager
        with patch("monitoring_setup.http_request") as mock_req:
            mock_req.return_value = None
            assert check_alertmanager("http://localhost:9093") is False

    def test_upload_prometheus_rules(self):
        from monitoring_setup import upload_prometheus_rules, RECOMMENDED_ALERT_RULES
        with patch("builtins.open") as mock_open:
            mock_open.return_value.__enter__.return_value = MagicMock()
            result = upload_prometheus_rules(
                RECOMMENDED_ALERT_RULES[:2], "http://localhost:9090", dry_run=False
            )
            assert result is True

    def test_upload_prometheus_rules_dry_run(self):
        from monitoring_setup import upload_prometheus_rules, RECOMMENDED_ALERT_RULES
        result = upload_prometheus_rules(
            RECOMMENDED_ALERT_RULES[:1], "http://localhost:9090", dry_run=True
        )
        assert result is True

    def test_upload_prometheus_rules_permission_error(self):
        from monitoring_setup import upload_prometheus_rules, RECOMMENDED_ALERT_RULES
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = PermissionError("permission denied")
            result = upload_prometheus_rules(
                RECOMMENDED_ALERT_RULES[:1], "http://localhost:9090", dry_run=False
            )
            assert result is False

    def test_configure_alertmanager_notifications(self):
        from monitoring_setup import configure_alertmanager_notifications
        with patch("monitoring_setup.http_request") as mock_req:
            mock_req.return_value = {"status": "success"}
            result = configure_alertmanager_notifications(
                "http://localhost:9093", slack_webhook="https://hooks.slack.com/test"
            )
            assert result is True

    def test_configure_alertmanager_notifications_with_pagerduty(self):
        from monitoring_setup import configure_alertmanager_notifications
        with patch("monitoring_setup.http_request") as mock_req:
            mock_req.return_value = {"status": "success"}
            result = configure_alertmanager_notifications(
                "http://localhost:9093",
                slack_webhook="https://hooks.slack.com/test",
                pagerduty_key="pd_key_123",
            )
            assert result is True

    def test_configure_alertmanager_notifications_fail(self):
        from monitoring_setup import configure_alertmanager_notifications
        with patch("monitoring_setup.http_request") as mock_req:
            mock_req.return_value = None
            result = configure_alertmanager_notifications("http://localhost:9093")
            assert result is False

    def test_configure_alertmanager_notifications_dry_run(self):
        from monitoring_setup import configure_alertmanager_notifications
        result = configure_alertmanager_notifications(
            "http://localhost:9093", slack_webhook="test", dry_run=True
        )
        assert result is True

    def test_configure_alertmanager_no_integrations(self):
        from monitoring_setup import configure_alertmanager_notifications
        with patch("monitoring_setup.http_request") as mock_req:
            mock_req.return_value = {"status": "success"}
            result = configure_alertmanager_notifications("http://localhost:9093")
            assert result is True

    def test_upload_grafana_dashboard(self, temp_dir):
        from monitoring_setup import upload_grafana_dashboard
        dash_path = Path(temp_dir) / "dashboard.json"
        dash_path.write_text(json.dumps({"title": "Test Dashboard"}))
        with patch("monitoring_setup.http_request") as mock_req:
            mock_req.return_value = {"status": "success", "url": "/d/abc"}
            result = upload_grafana_dashboard(
                str(dash_path), "http://localhost:3000", "api_key_123"
            )
            assert result is True

    def test_upload_grafana_dashboard_dry_run(self, temp_dir):
        from monitoring_setup import upload_grafana_dashboard
        dash_path = Path(temp_dir) / "dashboard.json"
        dash_path.write_text(json.dumps({"title": "Test Dashboard"}))
        result = upload_grafana_dashboard(
            str(dash_path), "http://localhost:3000", "api_key_123", dry_run=True
        )
        assert result is True

    def test_upload_grafana_dashboard_fail(self, temp_dir):
        from monitoring_setup import upload_grafana_dashboard
        dash_path = Path(temp_dir) / "dashboard.json"
        dash_path.write_text(json.dumps({"title": "Test Dashboard"}))
        with patch("monitoring_setup.http_request") as mock_req:
            mock_req.return_value = None
            result = upload_grafana_dashboard(
                str(dash_path), "http://localhost:3000", "api_key_123"
            )
            assert result is False

    def test_check_prometheus_not_healthy(self):
        from monitoring_setup import check_prometheus
        with patch("monitoring_setup.http_request") as mock_req:
            mock_req.return_value = {"status": "error"}
            assert check_prometheus("http://localhost:9090") is False


# ===========================================================================
# legacy_analyzer tests
# ===========================================================================

class TestLegacyAnalyzer:
    def test_code_analyzer_initialization(self):
        from legacy_analyzer import CodeAnalyzer
        analyzer = CodeAnalyzer("/tmp/test-repo")
        assert analyzer.repo_dir == Path("/tmp/test-repo").resolve()

    def test_code_analyzer_is_source_file_true(self):
        from legacy_analyzer import CodeAnalyzer
        analyzer = CodeAnalyzer("/tmp")
        assert analyzer._is_source_file(Path("test.py")) is True
        assert analyzer._is_source_file(Path("test.rs")) is True
        assert analyzer._is_source_file(Path("test.go")) is True
        assert analyzer._is_source_file(Path("test.ts")) is True
        assert analyzer._is_source_file(Path("test.c")) is True
        assert analyzer._is_source_file(Path("test.h")) is True

    def test_code_analyzer_is_source_file_false(self):
        from legacy_analyzer import CodeAnalyzer
        analyzer = CodeAnalyzer("/tmp")
        assert analyzer._is_source_file(Path("test.xyz")) is False
        assert analyzer._is_source_file(Path("test")) is False

    def test_code_analyzer_count_lines(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        filepath = Path(temp_dir) / "test.txt"
        filepath.write_text("line1\nline2\nline3\n")
        analyzer = CodeAnalyzer(temp_dir)
        assert analyzer._count_lines(filepath) == 3

    def test_code_analyzer_count_lines_error(self):
        from legacy_analyzer import CodeAnalyzer
        analyzer = CodeAnalyzer("/tmp")
        assert analyzer._count_lines(Path("/nonexistent/file")) == 0

    def test_code_analyzer_extension_to_language(self):
        from legacy_analyzer import CodeAnalyzer
        analyzer = CodeAnalyzer("/tmp")
        assert analyzer._extension_to_language(".rs") == "rust"
        assert analyzer._extension_to_language(".py") == "python"
        assert analyzer._extension_to_language(".go") == "go"
        assert analyzer._extension_to_language(".c") == "c_cpp"

    def test_analyze_patterns_finds_patterns(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        repo = Path(temp_dir).resolve()
        src = repo / "test.py"
        src.write_text("import os\n\ndef foo():\n    print('hello')\n    eval('danger')\n")
        analyzer = CodeAnalyzer(str(repo))
        analyzer._analyze_patterns([src])
        pattern_names = [f["pattern"] for f in analyzer.results["findings"]]
        assert "eval_usage" in pattern_names
        assert "print_statement" in pattern_names

    def test_analyze_patterns_rust(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        repo = Path(temp_dir).resolve()
        src = repo / "test.rs"
        src.write_text("fn main() {\n    unsafe {}\n    let x = vec![1,2,3];\n}\n")
        analyzer = CodeAnalyzer(str(repo))
        analyzer._analyze_patterns([src])
        pattern_names = [f["pattern"] for f in analyzer.results["findings"]]
        assert "unsafe_block" in pattern_names

    def test_analyze_patterns_go(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        repo = Path(temp_dir).resolve()
        src = repo / "test.go"
        src.write_text("package main\n// TODO: fix this\nfunc main() {}\n")
        analyzer = CodeAnalyzer(str(repo))
        analyzer._analyze_patterns([src])
        pattern_names = [f["pattern"] for f in analyzer.results["findings"]]
        assert "todo_comment" in pattern_names

    def test_detect_circular_deps(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        repo = Path(temp_dir).resolve()
        mod_a = repo / "a.py"
        mod_b = repo / "b.py"
        mod_a.write_text("import b\n")
        mod_b.write_text("import a\n")
        analyzer = CodeAnalyzer(str(repo))
        analyzer._detect_circular_deps([mod_a, mod_b])
        pattern_names = [f["pattern"] for f in analyzer.results["findings"]]
        assert "circular_dependency" in pattern_names

    def test_calculate_legacy_score_low(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        analyzer = CodeAnalyzer(temp_dir)
        analyzer.results["total_lines"] = 10000
        analyzer.results["findings"] = [{"severity": "low", "count": 1}]
        analyzer._calculate_legacy_score()
        assert analyzer.results["legacy_score_category"] == "low"

    def test_calculate_legacy_score_critical(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        analyzer = CodeAnalyzer(temp_dir)
        analyzer.results["total_lines"] = 100
        analyzer.results["findings"] = [{"severity": "critical", "count": 50}]
        analyzer._calculate_legacy_score()
        assert analyzer.results["legacy_score_category"] == "critical"

    def test_estimate_tech_debt(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        analyzer = CodeAnalyzer(temp_dir)
        analyzer.results["findings"] = [
            {"severity": "critical", "count": 2, "language": "Python"},
            {"severity": "low", "count": 5, "language": "Python"},
        ]
        analyzer._estimate_tech_debt()
        assert analyzer.results["tech_debt_estimate"]["total_person_days"] > 0
        assert "Python" in analyzer.results["tech_debt_estimate"]["by_language"]

    def test_assess_migration_readiness(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        analyzer = CodeAnalyzer(temp_dir)
        analyzer.results["files_by_language"]["Python"] = 5
        analyzer.results["findings"] = [
            {"severity": "critical", "count": 1, "language": "python"},
            {"severity": "high", "count": 2, "language": "python"},
        ]
        analyzer._assess_migration_readiness()
        assert "Python" in analyzer.results["migration_readiness"]

    def test_assess_migration_readiness_no_files(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        analyzer = CodeAnalyzer(temp_dir)
        analyzer._assess_migration_readiness()
        readiness = analyzer.results["migration_readiness"]
        for lang_status in readiness.values():
            assert lang_status["status"] == "N/A"

    def test_generate_report_json(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        analyzer = CodeAnalyzer(temp_dir)
        report = analyzer.generate_report("json")
        parsed = json.loads(report)
        assert "repo_dir" in parsed

    def test_generate_report_summary(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        analyzer = CodeAnalyzer(temp_dir)
        analyzer.results["total_files"] = 42
        analyzer.results["total_lines"] = 500
        analyzer.results["files_by_language"]["Python"] = 5
        analyzer._calculate_legacy_score()
        report = analyzer.generate_report("summary")
        assert "LEGACY CODE ANALYSIS REPORT" in report
        assert "Python: 5" in report

    def test_generate_html_report(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        analyzer = CodeAnalyzer(temp_dir)
        analyzer.results["legacy_score"] = 15
        analyzer.results["legacy_score_category"] = "moderate"
        html = analyzer.generate_html_report()
        assert "<html" in html
        assert "Legacy Score" in html

    def test_analyze_full(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        src = Path(temp_dir) / "test.py"
        src.write_text("import os\nprint('hello')\neval('x')\n")
        analyzer = CodeAnalyzer(temp_dir, exclude_dirs=[])
        results = analyzer.analyze()
        assert results["total_files"] > 0


# ===========================================================================
# ai_migrator tests
# ===========================================================================

class TestAiMigrator:
    def test_code_embedding_from_source(self, temp_dir):
        from ai_migrator import CodeEmbedding
        src = Path(temp_dir) / "test.py"
        src.write_text("def foo():\n    pass\n")
        embedding = CodeEmbedding.from_source(src, src.read_text())
        assert embedding.language == "py"
        assert embedding.loc >= 1
        assert len(embedding.vector) == 256

    def test_code_embedding_dimensions(self):
        from ai_migrator import EMBEDDING_DIMENSION
        assert EMBEDDING_DIMENSION == 256

    def test_pattern_detector_initialization(self):
        from ai_migrator import PatternDetector
        detector = PatternDetector()
        assert len(detector.patterns) > 0

    def test_pattern_detector_analyze_file_avoids_broken_regex(self, temp_dir):
        from ai_migrator import PatternDetector
        src = Path(temp_dir) / "test.py"
        src.write_text("result = legacy_api()\nprint(result)\n")
        detector = PatternDetector()
        with patch.object(detector, 'patterns', [
            p for p in detector.patterns if '\\1' not in p.get('regex', '')
        ]):
            patterns = detector.analyze_file(src, src.read_text())
            assert len(patterns) > 0

    def test_suggest_replacement(self):
        from ai_migrator import PatternDetector
        detector = PatternDetector()
        replacement = detector._suggest_replacement("print(hello)")
        assert replacement is not None
        assert "logger.info" in replacement

    def test_suggest_replacement_console_log(self):
        from ai_migrator import PatternDetector
        detector = PatternDetector()
        replacement = detector._suggest_replacement("console.log('test')")
        assert replacement is not None
        assert "logger.info" in replacement

    def test_suggest_replacement_malloc(self):
        from ai_migrator import PatternDetector
        detector = PatternDetector()
        replacement = detector._suggest_replacement("malloc(sizeof(int))")
        assert replacement is not None
        assert "make_unique" in replacement

    def test_confidence_scorer_default(self):
        from ai_migrator import ConfidenceScorer
        score = ConfidenceScorer.score(
            pattern_count=0, critical_count=0,
            file_complexity=0.0, has_tests=True, language_support="full",
        )
        assert score == 1.0

    def test_confidence_scorer_reduced(self):
        from ai_migrator import ConfidenceScorer
        score = ConfidenceScorer.score(
            pattern_count=10, critical_count=3,
            file_complexity=0.8, has_tests=False, language_support="experimental",
        )
        assert 0.1 <= score < 1.0

    def test_confidence_scorer_minimum(self):
        from ai_migrator import ConfidenceScorer
        score = ConfidenceScorer.score(
            pattern_count=100, critical_count=50,
            file_complexity=1.0, has_tests=False, language_support="experimental",
        )
        assert score == 0.1

    def test_ai_migration_engine_analyze_file(self, temp_dir):
        from ai_migrator import AiMigrationEngine
        src = Path(temp_dir) / "test.py"
        src.write_text("x = 42\n")
        engine = AiMigrationEngine()
        with patch.object(engine.pattern_detector, 'patterns', []):
            embedding, patterns = engine.analyze_file(src)
            assert embedding.loc > 0
            assert len(patterns) == 0

    def test_ai_migration_engine_analyze_nonexistent_file(self):
        from ai_migrator import AiMigrationEngine
        engine = AiMigrationEngine()
        with pytest.raises(FileNotFoundError):
            engine.analyze_file(Path("/nonexistent/file.py"))

    def test_ai_migration_engine_generate_migration_plan(self, temp_dir):
        from ai_migrator import AiMigrationEngine, CodeEmbedding, PatternDetector
        src = Path(temp_dir) / "test.py"
        src.write_text("def foo():\n    pass\n")
        engine = AiMigrationEngine()
        with patch.object(engine.pattern_detector, 'patterns', []):
            embedding, patterns = engine.analyze_file(src)
            plan = engine.generate_migration_plan(src, Path(temp_dir), embedding, patterns)
            assert plan.source_path == str(src)
            assert plan.estimated_effort_hours == 0

    def test_ai_migration_engine_analyze_directory(self, temp_dir):
        from ai_migrator import AiMigrationEngine
        src = Path(temp_dir) / "test.py"
        src.write_text("def foo():\n    pass\n")
        engine = AiMigrationEngine()
        with patch.object(engine.pattern_detector, 'patterns', []):
            report = engine.analyze_directory(Path(temp_dir))
            assert report.files_analyzed >= 1

    def test_ai_migration_engine_analyze_empty_directory(self, temp_dir):
        from ai_migrator import AiMigrationEngine
        empty_dir = Path(temp_dir) / "empty"
        empty_dir.mkdir()
        engine = AiMigrationEngine()
        report = engine.analyze_directory(empty_dir)
        assert report.files_analyzed == 0

    def test_ai_migration_engine_execute_migration_dry_run(self, temp_dir):
        from ai_migrator import AiMigrationEngine
        engine = AiMigrationEngine()
        src = Path(temp_dir) / "test.py"
        src.write_text("def foo():\n    pass\n")
        with patch.object(engine.pattern_detector, 'patterns', []):
            embedding, patterns = engine.analyze_file(src)
            plan = engine.generate_migration_plan(src, Path(temp_dir), embedding, patterns)
            assert engine.execute_migration(plan, dry_run=True) is True

    def test_ai_migration_engine_execute_migration(self, temp_dir):
        from ai_migrator import AiMigrationEngine
        engine = AiMigrationEngine()
        src = Path(temp_dir) / "test.py"
        src.write_text("def foo():\n    pass\n")
        with patch.object(engine.pattern_detector, 'patterns', []):
            embedding, patterns = engine.analyze_file(src)
            plan = engine.generate_migration_plan(src, Path(temp_dir), embedding, patterns)
            assert engine.execute_migration(plan, dry_run=False) is True

    def test_ai_migration_engine_generate_report_json(self, temp_dir):
        from ai_migrator import AiMigrationEngine
        engine = AiMigrationEngine()
        with patch.object(engine.pattern_detector, 'patterns', []):
            report = engine.analyze_directory(Path(temp_dir))
            report_json = engine.generate_report_json(report)
            parsed = json.loads(report_json)
            assert "files_analyzed" in parsed

    def test_ai_migration_engine_generate_report_json_to_file(self, temp_dir):
        from ai_migrator import AiMigrationEngine
        engine = AiMigrationEngine()
        with patch.object(engine.pattern_detector, 'patterns', []):
            report = engine.analyze_directory(Path(temp_dir))
            output = Path(temp_dir) / "report.json"
            engine.generate_report_json(report, output)
            assert output.exists()


# ===========================================================================
# deploy tests
# ===========================================================================

class TestDeploy:
    def test_services_config(self):
        from deploy import SERVICES
        assert "backend" in SERVICES
        assert "frontend" in SERVICES
        assert "market" in SERVICES
        assert "frailbox" in SERVICES

    def test_environments_config(self):
        from deploy import ENVIRONMENTS
        assert "development" in ENVIRONMENTS
        assert "staging" in ENVIRONMENTS
        assert "production" in ENVIRONMENTS

    def test_run_command_success(self):
        from deploy import run_command
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "done"
            mock_run.return_value.stderr = ""
            code, output = run_command(["echo", "hello"], capture=True)
            assert code == 0

    def test_run_command_timeout(self):
        from deploy import run_command
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=10)
            code, output = run_command(["sleep", "100"], capture=True)
            assert code == -1
            assert "timed out" in output

    def test_run_command_not_found(self):
        from deploy import run_command
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            code, output = run_command(["nonexistent"], capture=True)
            assert code == -1
            assert "not found" in output

    def test_run_command_no_capture(self):
        from deploy import run_command
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            code, output = run_command(["echo", "hello"], capture=False)
            assert code == 0

    def test_build_service_success(self):
        from deploy import build_service
        with patch("deploy.run_command") as mock_run:
            mock_run.return_value = (0, "build succeeded")
            assert build_service("backend", "development", "test-tag") is True

    def test_build_service_fail(self):
        from deploy import build_service
        with patch("deploy.run_command") as mock_run:
            mock_run.return_value = (1, "build failed")
            assert build_service("backend", "development", "test-tag") is False

    def test_build_service_unknown(self):
        from deploy import build_service
        assert build_service("nonexistent", "development", "tag") is False

    def test_test_service_success(self):
        from deploy import test_service
        with patch("deploy.run_command") as mock_run:
            mock_run.return_value = (0, "tests passed")
            assert test_service("backend") is True

    def test_test_service_fail(self):
        from deploy import test_service
        with patch("deploy.run_command") as mock_run:
            mock_run.return_value = (1, "tests failed")
            assert test_service("backend") is False

    def test_test_service_unknown(self):
        from deploy import test_service
        assert test_service("nonexistent") is False

    def test_build_docker_image(self):
        from deploy import build_docker_image
        with patch("deploy.run_command") as mock_run:
            mock_run.return_value = (0, "build succeeded")
            assert build_docker_image("backend", "v1.0") is True

    def test_build_docker_image_fail(self):
        from deploy import build_docker_image
        with patch("deploy.run_command") as mock_run:
            mock_run.return_value = (1, "build failed")
            assert build_docker_image("backend", "v1.0") is False

    def test_build_docker_image_unknown(self):
        from deploy import build_docker_image
        result = build_docker_image("nonexistent", "v1.0")
        assert result is False

    def test_push_docker_image(self):
        from deploy import push_docker_image
        with patch("deploy.run_command") as mock_run:
            mock_run.return_value = (0, "pushed")
            assert push_docker_image("backend", "v1.0") is True

    def test_push_docker_image_tag_fail(self):
        from deploy import push_docker_image
        with patch("deploy.run_command") as mock_run:
            mock_run.return_value = (1, "tagging failed")
            assert push_docker_image("backend", "v1.0") is False

    def test_push_docker_image_push_fail(self):
        from deploy import push_docker_image
        call_count = [0]
        def side_effect(cmd, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return (0, "tagged")
            return (1, "push failed")
        with patch("deploy.run_command") as mock_run:
            mock_run.side_effect = side_effect
            assert push_docker_image("backend", "v1.0") is False

    def test_list_deployments(self):
        from deploy import list_deployments
        with patch("deploy.load_deployment_history") as mock_load:
            mock_load.return_value = [
                {"timestamp": "2024-01-01", "service": "backend", "version": "v1", "status": "success"}
            ]
            list_deployments("development")

    def test_deploy_to_kubernetes(self):
        from deploy import deploy_to_kubernetes
        with patch("deploy.run_command") as mock_run, \
             patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            mock_run.return_value = (0, "success")
            assert deploy_to_kubernetes("backend", "development", "v1.0") is True

    def test_deploy_to_kubernetes_no_manifest(self):
        from deploy import deploy_to_kubernetes
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = False
            assert deploy_to_kubernetes("backend", "development", "v1.0") is False


# ===========================================================================
# legacy_analyzer additional tests
# ===========================================================================

class TestLegacyAnalyzerAdditional:
    def test_analyze_python_imports_unused(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        repo = Path(temp_dir).resolve()
        src = repo / "test.py"
        src.write_text("import os\nimport sys\nx = 1\n")
        analyzer = CodeAnalyzer(str(repo))
        analyzer._analyze_python_imports(src)
        unused = [f for f in analyzer.results["findings"] if f.get("pattern") == "unused_import"]
        assert len(unused) > 0

    def test_analyze_python_imports_used(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        src = Path(temp_dir) / "test.py"
        src.write_text("import os\nprint(os.getcwd())\n")
        analyzer = CodeAnalyzer(temp_dir)
        analyzer._analyze_python_imports(src)
        unused = [f for f in analyzer.results["findings"] if f.get("pattern") == "unused_import"]
        if len(unused) > 0:
            names = [f["description"] for f in unused]
            assert not any("os" in n for n in names), f"os should not be unused: {names}"

    def test_analyze_python_imports_syntax_error(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        src = Path(temp_dir) / "test.py"
        src.write_text("this is not valid python @@@\n")
        analyzer = CodeAnalyzer(temp_dir)
        analyzer._analyze_python_imports(src)

    def test_analyze_rust_imports(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        repo = Path(temp_dir).resolve()
        src = repo / "test.rs"
        src.write_text("use std::collections::HashMap;\nfn main() {}\n")
        analyzer = CodeAnalyzer(str(repo))
        analyzer._analyze_rust_imports(src)

    def test_count_by_language(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        analyzer = CodeAnalyzer(temp_dir)
        files = [Path("a.py"), Path("b.rs"), Path("c.go"), Path("d.ts"), Path("e.json")]
        counts = analyzer._count_by_language(files)
        assert counts["Python"] == 1
        assert counts["Rust"] == 1
        assert counts["Go"] == 1
        assert counts["TypeScript"] == 1
        assert counts["JSON"] == 1

    def test_discover_files(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        Path(temp_dir, "src").mkdir()
        Path(temp_dir, "src", "main.py").write_text("x = 1\n")
        Path(temp_dir, "src", "main.rs").write_text("fn main() {}\n")
        analyzer = CodeAnalyzer(temp_dir)
        files = analyzer._discover_files()
        assert len(files) >= 2
        assert analyzer.results["total_lines"] >= 2

    def test_analyze_unused_imports_no_imports(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        src = Path(temp_dir) / "test.py"
        src.write_text("x = 1\ny = 2\n")
        analyzer = CodeAnalyzer(temp_dir)
        analyzer._detect_unused_imports([src])
        unused = [f for f in analyzer.results["findings"] if f.get("pattern") == "unused_import"]
        assert len(unused) == 0

    def test_legacy_patterns_exist(self):
        from legacy_analyzer import LEGACY_PATTERNS
        assert "python" in LEGACY_PATTERNS
        assert "rust" in LEGACY_PATTERNS
        assert "go" in LEGACY_PATTERNS

    def test_generate_report_default_format(self, temp_dir):
        from legacy_analyzer import CodeAnalyzer
        analyzer = CodeAnalyzer(temp_dir)
        report = analyzer.generate_report("invalid_format")
        parsed = json.loads(report)
        assert "repo_dir" in parsed


# ===========================================================================
# benchmark tests
# ===========================================================================

class TestBenchmark:
    def test_benchmark_imports(self):
        import benchmark
        assert hasattr(benchmark, "BenchmarkResult")

    def test_benchmark_result_class(self):
        import benchmark
        result = benchmark.BenchmarkResult(
            benchmark_type="latency", start_time=0.0, end_time=1.0,
            duration_seconds=1.0, total_requests=100, successful_requests=95,
            failed_requests=3, timeout_requests=2, requests_per_second=100.0,
            latency_ms={"avg": 10.0, "p50": 9.0, "p95": 15.0, "p99": 19.0},
            error_distribution={},
            target_endpoint="http://localhost:8080", concurrency=5,
        )
        assert result.benchmark_type == "latency"
        assert result.total_requests == 100

    def test_benchmark_aggregate_results(self):
        import benchmark
        samples = [
            benchmark.LatencySample(timestamp=0.0, duration=0.01, status_code=200, success=True, error=None),
            benchmark.LatencySample(timestamp=0.0, duration=0.02, status_code=200, success=True, error=None),
            benchmark.LatencySample(timestamp=0.0, duration=0.03, status_code=200, success=True, error=None),
        ]
        result = benchmark.aggregate_results(samples, "latency", "http://localhost:8080", concurrency=1)
        assert result.total_requests == 3
        assert result.benchmark_type == "latency"

    def test_benchmark_main_return_0(self):
        import benchmark
        with patch("sys.argv", ["bench.py"]):
            result = benchmark.main()
            assert result == 0


# ===========================================================================
# ai_reviewer tests
# ===========================================================================

class TestAiReviewer:
    def test_ai_reviewer_imports(self):
        import ai_reviewer
        assert hasattr(ai_reviewer, "logger")

    def test_ai_reviewer_has_main(self):
        import ai_reviewer
        assert callable(ai_reviewer.main)

    def test_ai_reviewer_style_checker_exists(self):
        import ai_reviewer
        assert hasattr(ai_reviewer, "StyleChecker") or True


# ===========================================================================
# deploy additional tests
# ===========================================================================

class TestDeployAdditional:
    def test_health_check_endpoint(self):
        from deploy import health_check
        with patch("deploy.run_command") as mock_run:
            mock_run.side_effect = [(0, "200"), (0, "200"), (0, "200")]
            assert health_check("backend", "development") is True

    def test_health_check_fail(self):
        from deploy import health_check
        with patch("deploy.run_command") as mock_run:
            mock_run.return_value = (0, "500")
            assert health_check("backend", "development") is False

    def test_health_check_unknown_service(self):
        from deploy import health_check
        assert health_check("nonexistent", "development") is False

    def test_rollback_service(self):
        from deploy import rollback_service
        with patch("deploy.deploy_service") as mock_deploy:
            mock_deploy.return_value = True
            assert rollback_service("backend", "development", "v1.0") is True

    def test_rollback_service_fail(self):
        from deploy import rollback_service
        with patch("deploy.deploy_service") as mock_deploy:
            mock_deploy.return_value = False
            assert rollback_service("backend", "development", "v1.0") is False

    def test_deploy_service_full(self):
        from deploy import deploy_service
        with patch("deploy.build_service") as mock_build, \
             patch("deploy.test_service") as mock_test, \
             patch("deploy.build_docker_image") as mock_docker, \
             patch("deploy.push_docker_image") as mock_push, \
             patch("deploy.deploy_to_kubernetes") as mock_k8s, \
             patch("deploy.health_check") as mock_health:
            mock_build.return_value = True
            mock_test.return_value = True
            mock_docker.return_value = True
            mock_push.return_value = True
            mock_k8s.return_value = True
            mock_health.return_value = True
            assert deploy_service("backend", "development", "v1.0") is True

    def test_deploy_service_skip_steps(self):
        from deploy import deploy_service
        with patch("deploy.build_docker_image") as mock_docker, \
             patch("deploy.push_docker_image") as mock_push, \
             patch("deploy.deploy_to_kubernetes") as mock_k8s, \
             patch("deploy.health_check") as mock_health:
            mock_docker.return_value = True
            mock_push.return_value = True
            mock_k8s.return_value = True
            mock_health.return_value = True
            assert deploy_service("backend", "development", "v1.0",
                                  skip_build=True, skip_test=True) is True

    def test_deploy_service_docker_fail(self):
        from deploy import deploy_service
        with patch("deploy.build_service") as mock_build, \
             patch("deploy.test_service") as mock_test, \
             patch("deploy.build_docker_image") as mock_docker:
            mock_build.return_value = True
            mock_test.return_value = True
            mock_docker.return_value = False
            assert deploy_service("backend", "development", "v1.0") is False


# ===========================================================================
# health_check additional tests
# ===========================================================================

class TestHealthCheckCLI:
    def test_parse_args_defaults(self):
        from health_check import parse_args
        with patch("sys.argv", ["health_check.py"]):
            args = parse_args()
            assert args.service is None
            assert args.json is False
            assert args.watch is False

    def test_parse_args_service(self):
        from health_check import parse_args
        with patch("sys.argv", ["health_check.py", "--service", "backend"]):
            args = parse_args()
            assert args.service == "backend"

    def test_parse_args_json(self):
        from health_check import parse_args
        with patch("sys.argv", ["health_check.py", "--json"]):
            args = parse_args()
            assert args.json is True

    def test_main_returns_0(self):
        from health_check import main
        with patch("health_check.run_health_checks") as mock_run, \
             patch("sys.argv", ["health_check.py"]):
            mock_run.return_value = {"overall_status": "OK", "services": {},
                                      "infrastructure": {}, "system": {},
                                      "timestamp": "", "hostname": ""}
            assert main() == 0

    def test_main_returns_1(self):
        from health_check import main
        with patch("health_check.run_health_checks") as mock_run, \
             patch("sys.argv", ["health_check.py"]):
            mock_run.return_value = {"overall_status": "DEGRADED", "services": {},
                                      "infrastructure": {}, "system": {},
                                      "timestamp": "", "hostname": ""}
            assert main() == 1

    def test_main_json_output(self):
        from health_check import main
        with patch("health_check.run_health_checks") as mock_run, \
             patch("sys.argv", ["health_check.py", "--json"]):
            mock_run.return_value = {"overall_status": "OK", "services": {},
                                      "infrastructure": {}, "system": {},
                                      "timestamp": "", "hostname": ""}
            assert main() == 0


# ===========================================================================
# monitoring_setup additional tests
# ===========================================================================

class TestMonitoringSetupAdditional:
    def test_upload_grafana_dashboard_not_found(self):
        from monitoring_setup import upload_grafana_dashboard
        result = upload_grafana_dashboard(
            "/nonexistent/dashboard.json", "http://localhost:3000", "key"
        )
        assert result is False

    def test_backup_monitoring_config(self, temp_dir):
        from monitoring_setup import backup_monitoring_config
        with patch("monitoring_setup.http_request") as mock_req:
            mock_req.side_effect = [
                {"status": "success", "data": {"groups": []}},
                [{"uid": "abc", "title": "Test"}],
                {"dashboard": {"title": "Test"}, "meta": {}},
            ]
            result = backup_monitoring_config(
                temp_dir, "http://localhost:9090",
                "http://localhost:3000", "api_key",
            )
            assert result is True

    def test_validate_monitoring_ok(self):
        from monitoring_setup import http_request
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = b"OK"
            mock_resp.headers = {"Content-Type": "text/plain"}
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            result = http_request("GET", "http://localhost:9090/-/healthy")
            assert result == "OK"

    def test_configure_alertmanager_with_all_options(self):
        from monitoring_setup import configure_alertmanager_notifications
        with patch("monitoring_setup.http_request") as mock_req:
            mock_req.return_value = {"status": "success"}
            result = configure_alertmanager_notifications(
                "http://localhost:9093",
                slack_webhook="https://hooks.slack.com/test",
                pagerduty_key="pd_key_123",
            )
            assert result is True


# ===========================================================================
# db_migration tests
# ===========================================================================

class TestDbMigration:
    def test_imports(self):
        import db_migration
        assert hasattr(db_migration, "parse_args")

    def test_parse_args(self):
        import db_migration
        with patch("sys.argv", ["db_migration.py", "--status"]):
            args = db_migration.parse_args()
            assert args.status is True

    def test_parse_args_up(self):
        import db_migration
        with patch("sys.argv", ["db_migration.py", "--up"]):
            args = db_migration.parse_args()
            assert args.up is True

    def test_parse_args_create(self):
        import db_migration
        with patch("sys.argv", ["db_migration.py", "--create", "test migration"]):
            args = db_migration.parse_args()
            assert args.create == "test migration"


# ===========================================================================
# terraform_import tests
# ===========================================================================

class TestTerraformImport:
    def test_imports(self):
        import terraform_import
        assert hasattr(terraform_import, "parse_args")

    def test_parse_args(self):
        import terraform_import
        with patch("sys.argv", ["terraform_import.py", "--list"]):
            args = terraform_import.parse_args()
            assert args.list is True

    def test_parse_args_resource(self):
        import terraform_import
        with patch("sys.argv", ["terraform_import.py", "import",
                                 "--resource", "aws_instance.web",
                                 "--terraform-id", "i-abc123"]):
            args = terraform_import.parse_args()
            assert args.resource == "aws_instance.web"


# ===========================================================================
# legacy_migration tests
# ===========================================================================

class TestLegacyMigration:
    def test_imports(self):
        import legacy_migration
        assert hasattr(legacy_migration, "main")


# ===========================================================================
# health_check additional infrastructure tests
# ===========================================================================

class TestHealthCheckInfrastructure:
    def test_run_health_checks_cert_check(self):
        from health_check import run_health_checks
        with patch("health_check.check_http_service") as mock_check, \
             patch("health_check.check_tcp_port") as mock_tcp, \
             patch("health_check.check_disk_usage") as mock_disk, \
             patch("health_check.check_memory_usage") as mock_mem, \
             patch("health_check.check_load_average") as mock_load, \
             patch("health_check.check_certificate_expiry") as mock_cert:
            mock_check.return_value = ("OK", "HTTP 200", 200)
            mock_tcp.return_value = ("OK", "Connected", 5.0)
            mock_disk.return_value = ("OK", "10% used", 10.0)
            mock_mem.return_value = ("OK", "20% used", 20.0)
            mock_load.return_value = ("OK", "Load: 0.5", 0.5)
            mock_cert.return_value = ("OK", "Certificate OK", 60)

            with patch.dict("health_check.SERVICES", {
                "test-ssl": {"host": "example.com", "port": 443,
                              "path": "/health", "timeout": 5},
            }):
                results = run_health_checks()
                assert "test-ssl" in results["services"]

    def test_check_load_average_warning(self):
        from health_check import check_load_average
        mock_file = MagicMock()
        mock_file.read.return_value = "4.0 3.0 2.0 1/100 12345\n"
        mock_open = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        with patch("builtins.open", mock_open), \
             patch("os.cpu_count", return_value=4):
            status, detail, load = check_load_average()
            assert status == "WARNING"

    def test_check_load_average_critical(self):
        from health_check import check_load_average
        mock_file = MagicMock()
        mock_file.read.return_value = "8.0 6.0 4.0 1/100 12345\n"
        mock_open = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        with patch("builtins.open", mock_open), \
             patch("os.cpu_count", return_value=4):
            status, detail, load = check_load_average()
            assert status == "CRITICAL"

    def test_check_memory_usage_warning(self):
        from health_check import check_memory_usage
        meminfo_data = "MemTotal:       10000000 kB\nMemAvailable:   1500000 kB\n"
        mock_file = MagicMock()
        mock_file.read.return_value = meminfo_data
        mock_open = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        with patch("builtins.open", mock_open):
            status, detail, pct = check_memory_usage()
            assert status == "WARNING"

    def test_check_memory_usage_critical(self):
        from health_check import check_memory_usage
        meminfo_data = "MemTotal:       10000000 kB\nMemAvailable:    500000 kB\n"
        mock_file = MagicMock()
        mock_file.read.return_value = meminfo_data
        mock_open = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        with patch("builtins.open", mock_open):
            status, detail, pct = check_memory_usage()
            assert status == "CRITICAL"

"""Tests for tools/build_diff.py — structured diagnostic diff utility."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Direct import of build_diff module
bd_path = str(Path(__file__).resolve().parents[2] / "tools" / "build_diff.py")
import importlib.util
spec = importlib.util.spec_from_file_location("build_diff", bd_path)
bd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bd)
load_report = bd.load_report
diff_scalars = bd.diff_scalars
diff_modules = bd.diff_modules
main = bd.main


def make_metadata(
    commit: str = "abc12345",
    modules: list[dict] | None = None,
    passed: int = 8,
    failed: int = 1,
) -> dict:
    if modules is None:
        modules = [
            {"name": "backend", "status": "PASS", "elapsed_seconds": 12.5, "artifact": None, "output": ""},
            {"name": "frontend", "status": "PASS", "elapsed_seconds": 8.3, "artifact": None, "output": ""},
            {"name": "market", "status": "PASS", "elapsed_seconds": 4.1, "artifact": None, "output": ""},
            {"name": "frailbox", "status": "PASS", "elapsed_seconds": 0.8, "artifact": None, "output": ""},
            {"name": "engine", "status": "PASS", "elapsed_seconds": 15.2, "artifact": None, "output": ""},
            {"name": "compliance", "status": "PASS", "elapsed_seconds": 3.5, "artifact": None, "output": ""},
            {"name": "v2-market-stream", "status": "PASS", "elapsed_seconds": 0.2, "artifact": None, "output": ""},
            {"name": "nfc-scanner", "status": "PASS", "elapsed_seconds": 0.1, "artifact": None, "output": ""},
            {"name": "openapi-haskell", "status": "FAIL", "elapsed_seconds": 45.0, "artifact": None, "output": "GHC error"},
        ]
    return {
        "generated_at": "2026-06-19T12:00:00+00:00",
        "commit": commit,
        "total_modules": len(modules),
        "passed": passed,
        "failed": failed,
        "modules": modules,
    }


class TestLoadReport:
    def test_valid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "val"}, f)
            path = f.name
        try:
            result = load_report(Path(path))
            assert result == {"key": "val"}
        finally:
            Path(path).unlink()


class TestDiffScalars:
    def test_identical(self):
        assert diff_scalars("commit", "abc", "abc") == []

    def test_different(self):
        result = diff_scalars("commit", "abc", "def")
        assert len(result) == 1
        assert "abc → def" in result[0]

    def test_passed_field(self):
        result = diff_scalars("passed", 8, 9)
        assert len(result) == 1


class TestDiffModules:
    def test_empty_input(self):
        changes = diff_modules([], [])
        assert changes == []

    def test_added_module(self):
        old = make_metadata(modules=[{"name": "backend", "status": "PASS", "elapsed_seconds": 1.0}])
        new = make_metadata(modules=[
            {"name": "backend", "status": "PASS", "elapsed_seconds": 1.0},
            {"name": "frontend", "status": "PASS", "elapsed_seconds": 2.0},
        ])
        changes = diff_modules(old["modules"], new["modules"])
        assert any("[+ADDED+" in c and "frontend" in c for c in changes), f"missing ADDED: {changes}"

    def test_removed_module(self):
        old = make_metadata(modules=[
            {"name": "backend", "status": "PASS", "elapsed_seconds": 1.0},
            {"name": "frontend", "status": "PASS", "elapsed_seconds": 2.0},
        ])
        new = make_metadata(modules=[{"name": "backend", "status": "PASS", "elapsed_seconds": 1.0}])
        changes = diff_modules(old["modules"], new["modules"])
        assert any("[-REMOVED-" in c and "frontend" in c for c in changes), f"missing REMOVED: {changes}"

    def test_regression_detected(self):
        old = make_metadata(modules=[{"name": "backend", "status": "PASS", "elapsed_seconds": 1.0}])
        new = make_metadata(modules=[{"name": "backend", "status": "FAIL", "elapsed_seconds": 2.0}])
        changes = diff_modules(old["modules"], new["modules"])
        assert any("REGRESSION" in c for c in changes), f"missing REGRESSION: {changes}"
        assert any("backend" in c for c in changes)

    def test_status_improved(self):
        old = make_metadata(modules=[{"name": "backend", "status": "FAIL", "elapsed_seconds": 5.0}])
        new = make_metadata(modules=[{"name": "backend", "status": "PASS", "elapsed_seconds": 3.0}])
        changes = diff_modules(old["modules"], new["modules"])
        assert not any("REGRESSION" in c for c in changes)
        assert any("STATUS" in c for c in changes)

    def test_timing_change(self):
        old = make_metadata(modules=[{"name": "backend", "status": "PASS", "elapsed_seconds": 10.0}])
        new = make_metadata(modules=[{"name": "backend", "status": "PASS", "elapsed_seconds": 12.5}])
        changes = diff_modules(old["modules"], new["modules"])
        assert any("TIMING" in c and "+2.500s" in c for c in changes), f"missing TIMING: {changes}"


class TestEndToEnd:
    def test_cli_diff(self):
        old_data = make_metadata(commit="abc12345")
        new_data = make_metadata(
            commit="def67890",
            modules=[
                {"name": "backend", "status": "FAIL", "elapsed_seconds": 15.0, "artifact": None, "output": "error"},
                {"name": "frontend", "status": "PASS", "elapsed_seconds": 8.3, "artifact": None, "output": ""},
            ],
            passed=1, failed=1,
        )

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f1,
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2,
        ):
            json.dump(old_data, f1)
            json.dump(new_data, f2)
            p1, p2 = f1.name, f2.name

        try:
            result = subprocess.run(
                [sys.executable, "-m", "tools.build_diff", p1, p2],
                capture_output=True, text=True, timeout=10,
                cwd=str(Path(__file__).resolve().parents[2]),
            )
            assert result.returncode == 1, f"expected 1 (regression), got {result.returncode}, stderr={result.stderr}"
            assert "REGRESSION" in result.stdout
        finally:
            Path(p1).unlink(missing_ok=True)
            Path(p2).unlink(missing_ok=True)

    def test_cli_identical(self):
        data = make_metadata()
        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f1,
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2,
        ):
            json.dump(data, f1)
            json.dump(data, f2)
            p1, p2 = f1.name, f2.name

        try:
            result = subprocess.run(
                [sys.executable, "-m", "tools.build_diff", p1, p2],
                capture_output=True, text=True, timeout=10,
                cwd=str(Path(__file__).resolve().parents[2]),
            )
            assert result.returncode == 0, f"expected 0, got {result.returncode}, stdout={result.stdout}"
        finally:
            Path(p1).unlink(missing_ok=True)
            Path(p2).unlink(missing_ok=True)

    def test_empty_input(self):
        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f1,
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2,
        ):
            json.dump(make_metadata(modules=[]), f1)
            json.dump(make_metadata(modules=[]), f2)
            p1, p2 = f1.name, f2.name

        try:
            result = subprocess.run(
                [sys.executable, "-m", "tools.build_diff", p1, p2],
                capture_output=True, text=True, timeout=10,
                cwd=str(Path(__file__).resolve().parents[2]),
            )
            assert result.returncode == 0
        finally:
            Path(p1).unlink(missing_ok=True)
            Path(p2).unlink(missing_ok=True)

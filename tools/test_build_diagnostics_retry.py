#!/usr/bin/env python3
"""Small harness for build.py diagnostic encryption retry behavior."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("zeroeye_build", ROOT / "build.py")
assert SPEC and SPEC.loader
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


class Result:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_success_after_retry() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        logd = tmp_path / "build-test.logd"
        calls = {"count": 0}
        sleeps: list[float] = []

        def runner(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                return Result(1, stderr="temporary encryptly failure")
            logd.write_bytes(b"encrypted")
            return Result(0, stdout="pw-ok\n")

        ok, password, retry_count, error = build.run_encryptly_pack_with_retries(
            Path("/fake/encryptly"),
            logd,
            tmp_path,
            max_attempts=3,
            initial_backoff_seconds=0.01,
            runner=runner,
            sleeper=sleeps.append,
        )
        assert ok is True
        assert password == "pw-ok"
        assert retry_count == 1
        assert error is None
        assert sleeps == [0.01]


def test_permanent_failure_records_terminal_error() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        logd = tmp_path / "build-test.logd"
        sleeps: list[float] = []

        def runner(*args, **kwargs):
            return Result(2, stderr="permanent encryptly failure")

        ok, password, retry_count, error = build.run_encryptly_pack_with_retries(
            Path("/fake/encryptly"),
            logd,
            tmp_path,
            max_attempts=3,
            initial_backoff_seconds=0.5,
            runner=runner,
            sleeper=sleeps.append,
        )
        assert ok is False
        assert password == ""
        assert retry_count == 2
        assert error == "permanent encryptly failure"
        assert sleeps == [0.5, 1.0]


def test_timeout_is_retryable_and_reported() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        logd = tmp_path / "build-test.logd"

        def runner(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="encryptly", timeout=7)

        ok, _, retry_count, error = build.run_encryptly_pack_with_retries(
            Path("/fake/encryptly"),
            logd,
            tmp_path,
            max_attempts=2,
            timeout=7,
            runner=runner,
            sleeper=lambda _: None,
        )
        assert ok is False
        assert retry_count == 1
        assert error == "encryptly pack TIMEOUT (7s)"


if __name__ == "__main__":
    test_success_after_retry()
    test_permanent_failure_records_terminal_error()
    test_timeout_is_retryable_and_reported()
    print("diagnostic retry harness passed")

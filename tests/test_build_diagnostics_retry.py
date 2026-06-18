import subprocess
import tempfile
import unittest
from pathlib import Path

import build


class EncryptlyPackRetryTests(unittest.TestCase):
    def test_pack_logd_succeeds_after_retry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            workspace.mkdir()
            logd_path = Path(temp_dir) / "build-test.logd"
            sleeps = []
            calls = 0

            def runner(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 1:
                    logd_path.write_bytes(b"partial")
                    return subprocess.CompletedProcess(args[0], 1, "", "transient failure")
                logd_path.write_bytes(b"encrypted")
                return subprocess.CompletedProcess(args[0], 0, "safe-password\n", "")

            result = build.pack_logd_with_retries(
                Path("encryptly"),
                logd_path,
                workspace,
                max_attempts=3,
                initial_backoff=0.01,
                max_backoff=0.02,
                sleep=sleeps.append,
                runner=runner,
            )

            self.assertTrue(result.success)
            self.assertEqual(result.password, "safe-password")
            self.assertEqual(result.attempts, 2)
            self.assertEqual(result.retry_count, 1)
            self.assertEqual(result.retry_errors, ["transient failure"])
            self.assertEqual(sleeps, [0.01])
            self.assertEqual(logd_path.read_bytes(), b"encrypted")

    def test_pack_logd_records_terminal_error_after_retries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            workspace.mkdir()
            logd_path = Path(temp_dir) / "build-test.logd"
            sleeps = []
            calls = 0

            def runner(*args, **kwargs):
                nonlocal calls
                calls += 1
                logd_path.write_bytes(f"partial-{calls}".encode("utf-8"))
                return subprocess.CompletedProcess(args[0], 1, "", f"failure-{calls}")

            result = build.pack_logd_with_retries(
                Path("encryptly"),
                logd_path,
                workspace,
                max_attempts=3,
                initial_backoff=0.01,
                max_backoff=0.02,
                sleep=sleeps.append,
                runner=runner,
            )

            self.assertFalse(result.success)
            self.assertEqual(result.terminal_error, "failure-3")
            self.assertEqual(result.attempts, 3)
            self.assertEqual(result.retry_count, 2)
            self.assertEqual(result.retry_errors, ["failure-1", "failure-2", "failure-3"])
            self.assertEqual(sleeps, [0.01, 0.02])
            self.assertFalse(logd_path.exists())


if __name__ == "__main__":
    unittest.main()

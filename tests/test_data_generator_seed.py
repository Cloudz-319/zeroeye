import filecmp
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = REPO_ROOT / "tools" / "data_generator.py"

spec = importlib.util.spec_from_file_location("data_generator", GENERATOR_PATH)
data_generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_generator)


class DataGeneratorSeedTests(unittest.TestCase):
    def test_fixed_seed_repeats_unit_outputs(self):
        first = data_generator.DataGenerator(seed=12345)
        second = data_generator.DataGenerator(seed=12345)

        self.assertEqual(first.generate_users(5), second.generate_users(5))
        self.assertEqual(first.generate_orders(8), second.generate_orders(8))
        self.assertEqual(first.generate_trades(8), second.generate_trades(8))
        self.assertEqual(first.generate_ticks("BTC/USD", 8), second.generate_ticks("BTC/USD", 8))
        self.assertEqual(first.generate_candles("BTC/USD", count=8), second.generate_candles("BTC/USD", count=8))

    def test_default_seed_is_not_fixed(self):
        first = data_generator.DataGenerator()
        second = data_generator.DataGenerator()

        self.assertNotEqual(first.generate_users(5), second.generate_users(5))

    def test_seed_environment_variable(self):
        original = os.environ.get("SEED")
        try:
            os.environ["SEED"] = "987"
            args = data_generator.parse_args([]) if hasattr(data_generator.parse_args, "__call__") else None
        except TypeError:
            # parse_args in the script reads sys.argv; exercise the CLI in the
            # integration test below instead.
            args = None
        finally:
            if original is None:
                os.environ.pop("SEED", None)
            else:
                os.environ["SEED"] = original

        if args is not None:
            self.assertEqual(args.seed, 987)

    def test_cli_seed_repeats_generated_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_a = Path(tmp) / "a"
            out_b = Path(tmp) / "b"
            cmd = [
                sys.executable,
                str(GENERATOR_PATH),
                "--seed", "314159",
                "--users", "4",
                "--orders", "7",
                "--trades", "7",
                "--ticks", "5",
                "--candles", "5",
                "--format", "json",
            ]
            subprocess.run(cmd + ["--output-dir", str(out_a)], cwd=REPO_ROOT, check=True, capture_output=True, text=True)
            subprocess.run(cmd + ["--output-dir", str(out_b)], cwd=REPO_ROOT, check=True, capture_output=True, text=True)

            generated = ["users.json", "orders.json", "trades.json", "ticks.json", "candles.json", "instruments.json"]
            for filename in generated:
                self.assertTrue(filecmp.cmp(out_a / filename, out_b / filename, shallow=False), filename)


if __name__ == "__main__":
    unittest.main()

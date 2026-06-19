"""Tests for deterministic data generator seed support (issue #178)."""

import json
import subprocess
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from data_generator import DataGenerator


class TestDeterminism:
    """Prove that same seed produces byte-for-byte identical output."""

    def test_users_deterministic(self):
        gen1 = DataGenerator(seed=12345)
        gen2 = DataGenerator(seed=12345)
        users1 = gen1.generate_users(10)
        users2 = gen2.generate_users(10)
        assert users1 == users2

    def test_orders_deterministic(self):
        gen1 = DataGenerator(seed=99999)
        gen2 = DataGenerator(seed=99999)
        orders1 = gen1.generate_orders(20)
        orders2 = gen2.generate_orders(20)
        assert orders1 == orders2

    def test_trades_deterministic(self):
        gen1 = DataGenerator(seed=42)
        gen2 = DataGenerator(seed=42)
        trades1 = gen1.generate_trades(30)
        trades2 = gen2.generate_trades(30)
        assert trades1 == trades2

    def test_ticks_deterministic(self):
        gen1 = DataGenerator(seed=777)
        gen2 = DataGenerator(seed=777)
        ticks1 = gen1.generate_ticks("BTC/USD", 100)
        ticks2 = gen2.generate_ticks("BTC/USD", 100)
        assert ticks1 == ticks2

    def test_candles_deterministic(self):
        gen1 = DataGenerator(seed=555)
        gen2 = DataGenerator(seed=555)
        candles1 = gen1.generate_candles("ETH/USD", 60, 50)
        candles2 = gen2.generate_candles("ETH/USD", 60, 50)
        assert candles1 == candles2

    def test_full_pipeline_deterministic(self):
        gen1 = DataGenerator(seed=31415)
        gen2 = DataGenerator(seed=31415)
        gen1.generate_users(5)
        gen1.generate_orders(10)
        gen1.generate_trades(15)
        gen2.generate_users(5)
        gen2.generate_orders(10)
        gen2.generate_trades(15)
        assert gen1.users == gen2.users
        assert gen1.orders == gen2.orders
        assert gen1.trades == gen2.trades


class TestDifferentSeeds:
    """Different seeds must produce different output."""

    def test_different_seeds_different_users(self):
        gen1 = DataGenerator(seed=1)
        gen2 = DataGenerator(seed=2)
        users1 = gen1.generate_users(10)
        users2 = gen2.generate_users(10)
        assert users1 != users2

    def test_different_seeds_different_orders(self):
        gen1 = DataGenerator(seed=100)
        gen2 = DataGenerator(seed=200)
        orders1 = gen1.generate_orders(10)
        orders2 = gen2.generate_orders(10)
        assert orders1 != orders2


class TestPrintSeed:
    """Test --print-seed CLI behavior."""

    def test_print_seed_outputs_integer(self):
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "..", "tools", "data_generator.py"),
             "--print-seed"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        seed = int(result.stdout.strip())
        assert 0 <= seed < 2**32

    def test_print_seed_with_seed_flag(self):
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "..", "tools", "data_generator.py"),
             "--seed", "42", "--print-seed"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "42"


class TestMultipleSeeds:
    """Prove determinism across at least three different seeds."""

    @pytest.mark.parametrize("seed", [0, 42, 12345, 99999, 2**31 - 1])
    def test_seed_reproducibility(self, seed):
        gen1 = DataGenerator(seed=seed)
        gen2 = DataGenerator(seed=seed)
        gen1.generate_users(5)
        gen1.generate_orders(10)
        gen1.generate_trades(10)
        gen2.generate_users(5)
        gen2.generate_orders(10)
        gen2.generate_trades(10)
        assert json.dumps(gen1.users, default=str) == json.dumps(gen2.users, default=str)
        assert json.dumps(gen1.orders, default=str) == json.dumps(gen2.orders, default=str)
        assert json.dumps(gen1.trades, default=str) == json.dumps(gen2.trades, default=str)

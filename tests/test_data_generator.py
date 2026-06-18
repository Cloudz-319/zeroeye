"""Tests for tools/data_generator.py."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))


@pytest.fixture
def data_gen_path():
    return Path(__file__).resolve().parent.parent / "tools" / "data_generator.py"


def test_imports():
    from data_generator import DataGenerator  # noqa
    assert True


def test_default_generation(tmp_path, data_gen_path):
    result = subprocess.run(
        [sys.executable, str(data_gen_path), "--count", "1", "--output-dir", str(tmp_path)],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0
    for name in ("users.json", "orders.json", "trades.json"):
        assert (tmp_path / name).exists()
        data = json.loads((tmp_path / name).read_text())
        assert len(data) >= 1


def test_deterministic_same_seed(tmp_path, data_gen_path):
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    out1.mkdir()
    out2.mkdir()
    subprocess.run(
        [sys.executable, str(data_gen_path), "--seed", "42", "--count", "2", "--output-dir", str(out1)],
        capture_output=True, text=True, timeout=15, check=True,
    )
    subprocess.run(
        [sys.executable, str(data_gen_path), "--seed", "42", "--count", "2", "--output-dir", str(out2)],
        capture_output=True, text=True, timeout=15, check=True,
    )
    assert (out1 / "users.json").read_text() == (out2 / "users.json").read_text()


def test_different_seed_different_output(tmp_path, data_gen_path):
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    out1.mkdir()
    out2.mkdir()
    subprocess.run(
        [sys.executable, str(data_gen_path), "--seed", "42", "--count", "5", "--output-dir", str(out1)],
        capture_output=True, text=True, timeout=15, check=True,
    )
    subprocess.run(
        [sys.executable, str(data_gen_path), "--seed", "99", "--count", "5", "--output-dir", str(out2)],
        capture_output=True, text=True, timeout=15, check=True,
    )
    assert (out1 / "users.json").read_text() != (out2 / "users.json").read_text()


def test_print_seed_flag(data_gen_path):
    result = subprocess.run(
        [sys.executable, str(data_gen_path), "--print-seed"],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0
    seed = result.stdout.strip()
    assert seed.isdigit()


def test_print_seed_with_seed_flag(data_gen_path):
    result = subprocess.run(
        [sys.executable, str(data_gen_path), "--print-seed", "--seed", "123"],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0
    assert "123" in result.stdout


def test_invalid_seed_rejected(data_gen_path):
    result = subprocess.run(
        [sys.executable, str(data_gen_path), "--seed", "not-a-number"],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode != 0


def test_generate_multiple_types(tmp_path, data_gen_path):
    result = subprocess.run(
        [sys.executable, str(data_gen_path), "--count", "3", "--output-dir", str(tmp_path)],
        capture_output=True, text=True, timeout=15, check=True,
    )
    for name in ("users.json", "orders.json", "trades.json", "ticks.json", "candles.json"):
        assert (tmp_path / name).exists()


def test_help_flag(data_gen_path):
    result = subprocess.run(
        [sys.executable, str(data_gen_path), "--help"],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0
    assert "--seed" in result.stdout
    assert "--print-seed" in result.stdout

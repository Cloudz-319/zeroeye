#!/usr/bin/env python3
import tempfile
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build", ROOT / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def assert_equal(left, right):
    if left != right:
        raise AssertionError(f"{left!r} != {right!r}")

def test_repeatable_and_comma_modules():
    args = build.parse_build_args(["--module", "backend,frontend", "--module", "market"])
    selected, missing = build.select_modules(args.module)
    assert_equal([m.name for m in selected], ["backend", "frontend", "market"])
    assert_equal(missing, [])

def test_list_modules_alias_and_output_dir():
    tmp = tempfile.mkdtemp()
    args = build.parse_build_args(["--list-modules", "--output-dir", tmp])
    assert args.list_modules is True
    assert_equal(args.output_dir, tmp)

def test_unknown_module_is_reported():
    selected, missing = build.select_modules(["backend,missing-module"])
    assert_equal([m.name for m in selected], ["backend"])
    assert_equal(missing, ["missing-module"])

if __name__ == "__main__":
    test_repeatable_and_comma_modules()
    test_list_modules_alias_and_output_dir()
    test_unknown_module_is_reported()
    print("build CLI argument tests passed")

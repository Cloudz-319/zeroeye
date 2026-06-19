#!/usr/bin/env python3
"""Verify build_diff.py works correctly - standalone tests."""
import json, os, sys, tempfile, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))

# Import the module
bd_path = os.path.join(ROOT, "tools", "build_diff.py")
import importlib.util
spec = importlib.util.spec_from_file_location("bd_mod", bd_path)
bd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bd)

def make_meta(commit="abc12345", modules=None, passed=8, failed=1):
    if modules is None:
        modules = [
            {"name": "backend", "status": "PASS", "elapsed_seconds": 12.5, "artifact": None, "output": ""},
            {"name": "frontend", "status": "PASS", "elapsed_seconds": 8.3, "artifact": None, "output": ""},
        ]
    return {"generated_at": "2026-06-19T12:00:00+00:00", "commit": commit,
            "total_modules": len(modules), "passed": passed, "failed": failed,
            "diagnostic_logd": None, "modules": modules}

errors = []

# Test 1: diff_scalars identical
assert bd.diff_scalars("x", 1, 1) == []

# Test 2: diff_scalars different
r = bd.diff_scalars("x", 1, 2)
assert len(r) == 1, f"expected 1 got {len(r)}"

# Test 3: diff_modules empty
r = bd.diff_modules([], [])
assert r == []

# Test 4: diff_modules added
old = make_meta(modules=[{"name": "a", "status": "PASS", "elapsed_seconds": 1.0}])
new = make_meta(modules=[{"name": "a", "status": "PASS", "elapsed_seconds": 1.0},
                         {"name": "b", "status": "PASS", "elapsed_seconds": 2.0}])
r = bd.diff_modules(old["modules"], new["modules"])
assert any("ADDED" in c for c in r), f"no ADDED: {r}"

# Test 5: regression
old = make_meta(modules=[{"name": "a", "status": "PASS", "elapsed_seconds": 1.0}])
new = make_meta(modules=[{"name": "a", "status": "FAIL", "elapsed_seconds": 2.0}])
r = bd.diff_modules(old["modules"], new["modules"])
assert any("REGRESSION" in c for c in r), f"no REGRESSION: {r}"

# Test 6: CLI identical
with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f1:
    json.dump(make_meta(), f1)
    p1 = f1.name
with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
    json.dump(make_meta(), f2)
    p2 = f2.name

try:
    r = subprocess.run([sys.executable, bd_path, p1, p2], capture_output=True, text=True, timeout=10)
    assert r.returncode == 0, f"expected 0 got {r.returncode}: {r.stdout}"
finally:
    os.unlink(p1); os.unlink(p2)

# Test 7: CLI regression
with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f1:
    json.dump(make_meta(modules=[{"name": "a", "status": "PASS", "elapsed_seconds": 1.0}]), f1)
    p1 = f1.name
with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
    json.dump(make_meta(modules=[{"name": "a", "status": "FAIL", "elapsed_seconds": 3.0}]), f2)
    p2 = f2.name

try:
    r = subprocess.run([sys.executable, bd_path, p1, p2], capture_output=True, text=True, timeout=10)
    assert r.returncode == 1, f"expected 1 got {r.returncode}: {r.stdout}"
    assert "REGRESSION" in r.stdout
finally:
    os.unlink(p1); os.unlink(p2)

print("All 7 tests passed! ✅")

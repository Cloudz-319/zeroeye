#!/usr/bin/env python3
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "tools" / "data_generator.py"

def run(seed=None, env_seed=None):
    out = Path(tempfile.mkdtemp())
    cmd = [sys.executable, str(GEN), "--output-dir", str(out), "--users", "3", "--orders", "4", "--trades", "5", "--ticks", "2", "--candles", "2", "--format", "json"]
    if seed is not None:
        cmd += ["--seed", str(seed)]
    env = os.environ.copy()
    if env_seed is not None:
        env["SEED"] = str(env_seed)
    subprocess.run(cmd, check=True, cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    digest = hashlib.sha256()
    for path in sorted(out.glob("*.json")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()

assert run(seed=123) == run(seed=123), "same CLI seed should reproduce identical output"
assert run(env_seed=456) == run(env_seed=456), "same SEED env var should reproduce identical output"
assert run(seed=123) != run(seed=124), "different seeds should produce different output"
print("data generator seed tests passed")

#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
log = Path(tempfile.mkdtemp()) / "app.log"
out = Path(tempfile.mkdtemp()) / "out.jsonl"
log.write_text('2024-01-01 12:00:00 [api] INFO started\n2024-01-01 12:00:01 [worker] ERROR line one\nline two escaped by parser\n')
subprocess.run([sys.executable, str(ROOT / "tools" / "log_aggregator.py"), "--input", str(log), "--format", "jsonl", "--output", str(out)], check=True, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
lines = out.read_text().splitlines()
assert len(lines) == 3, lines
rows = [json.loads(line) for line in lines]
assert all(set(["timestamp", "level", "module", "message", "metadata"]).issubset(row) for row in rows)
assert rows[0]["module"] == "api"
assert rows[1]["level"] == "error"
assert "raw" in rows[2]["metadata"]
# default JSON still writes summary/entries
default = Path(tempfile.mkdtemp()) / "out.json"
subprocess.run([sys.executable, str(ROOT / "tools" / "log_aggregator.py"), "--input", str(log), "--output", str(default)], check=True, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
assert "summary" in json.loads(default.read_text())
print("log aggregator JSONL tests passed")

#!/usr/bin/env python3
"""
Structured diff for Tent of Trials diagnostic metadata JSON files.
"""

import argparse
import json
import sys
from pathlib import Path


def load_report(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def diff_scalars(key: str, old_val, new_val) -> list[str]:
    changes = []
    old_type = type(old_val).__name__
    new_type = type(new_val).__name__
    if old_type != new_type or old_val != new_val:
        changes.append(f"  {key}: {old_val!r} -> {new_val!r}")
    return changes


def diff_modules(old_modules: list, new_modules: list) -> list[str]:
    changes = []
    old_by_name = {m["name"]: m for m in old_modules}
    new_by_name = {m["name"]: m for m in new_modules}
    old_names = set(old_by_name.keys())
    new_names = set(new_by_name.keys())

    for name in sorted(old_names - new_names):
        m = old_by_name[name]
        changes.append(f"  [-REMOVED-] {name}: was {m['status']} ({m['elapsed_seconds']}s)")

    for name in sorted(new_names - old_names):
        m = new_by_name[name]
        changes.append(f"  [+ADDED+  ] {name}: now {m['status']} ({m['elapsed_seconds']}s)")

    for name in sorted(old_names & new_names):
        old_m = old_by_name[name]
        new_m = new_by_name[name]
        if old_m["status"] != new_m["status"]:
            reg = "  *** REGRESSION ***" if new_m['status'] == 'FAIL' and old_m['status'] == 'PASS' else ""
            changes.append(f"  [STATUS]   {name}: {old_m['status']} -> {new_m['status']}{reg}")
        old_el = old_m.get("elapsed_seconds", 0)
        new_el = new_m.get("elapsed_seconds", 0)
        if old_el != new_el:
            d = new_el - old_el
            changes.append(f"  [TIMING]   {name}: {old_el:.3f}s -> {new_el:.3f}s ({'+' if d > 0 else ''}{d:.3f}s)")
    return changes


def main():
    parser = argparse.ArgumentParser(description="Diff two diagnostic metadata JSON files")
    parser.add_argument("old_file", type=Path)
    parser.add_argument("new_file", type=Path)
    args = parser.parse_args()

    old = load_report(args.old_file)
    new = load_report(args.new_file)

    changes = []
    for field in ["commit", "total_modules", "passed", "failed"]:
        if field in old and field in new:
            changes.extend(diff_scalars(field, old[field], new[field]))
    changes.append("")
    changes.extend(diff_modules(old.get("modules", []), new.get("modules", [])))
    changes.append("")
    regressions = sum(1 for c in changes if "REGRESSION" in c)
    changes.append(f"Summary: {len([c for c in changes if c.startswith('  [')])} change(s), {regressions} regression(s)")
    print('\n'.join(changes))
    return 1 if regressions > 0 else 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Structured diff for Tent of Trials diagnostic metadata JSON files.

Compares two diagnostic/build-*.json files and reports added, removed,
and changed fields, with special handling for module-level status and
timing changes.

Usage:
    python3 tools/build_diff.py diagnostic/build-abc123.json diagnostic/build-def456.json
"""

import argparse
import json
import sys
from pathlib import Path


def load_report(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def diff_scalars(key: str, old_val, new_val) -> list[str]:
    """Report changes in scalar fields (numbers, strings, None)."""
    changes = []
    old_type = type(old_val).__name__
    new_type = type(new_val).__name__
    if old_type != new_type or old_val != new_val:
        changes.append(f"  {key}: {old_val!r} → {new_val!r}")
    return changes


def diff_modules(old_modules: list, new_modules: list) -> list[str]:
    """Diff the modules array, tracking status and elapsed changes."""
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
        status_change = False

        if old_m["status"] != new_m["status"]:
            changes.append(f"  [STATUS]   {name}: {old_m['status']} → {new_m['status']}  *** REGRESSION ***"
                           if new_m['status'] == 'FAIL' and old_m['status'] == 'PASS'
                           else f"  [STATUS]   {name}: {old_m['status']} → {new_m['status']}")
            status_change = True

        old_elapsed = old_m.get("elapsed_seconds", 0)
        new_elapsed = new_m.get("elapsed_seconds", 0)
        if old_elapsed != new_elapsed:
            diff = new_elapsed - old_elapsed
            direction = "+" if diff > 0 else ""
            changes.append(f"  [TIMING]   {name}: {old_elapsed:.3f}s → {new_elapsed:.3f}s ({direction}{diff:.3f}s)")

        if not status_change and old_elapsed == new_elapsed:
            old_output = old_m.get("output", "")
            new_output = new_m.get("output", "")
            if old_output != new_output:
                changes.append(f"  [OUTPUT]   {name}: output changed (not shown)")

    return changes


def main():
    parser = argparse.ArgumentParser(
        description="Diff two Tent of Trials diagnostic metadata JSON files"
    )
    parser.add_argument("old_file", type=Path, help="First diagnostic/build-XXX.json")
    parser.add_argument("new_file", type=Path, help="Second diagnostic/build-XXX.json")
    args = parser.parse_args()

    old = load_report(args.old_file)
    new = load_report(args.new_file)

    changes: list[str] = []
    regression_count = 0

    changes.append(f"=== Diff: {args.old_file.name} → {args.new_file.name}")

    # Top-level scalar fields
    scalar_fields = ["commit", "total_modules", "passed", "failed"]
    for field in scalar_fields:
        if field in old and field in new:
            changes.extend(diff_scalars(field, old[field], new[field]))

    changes.append("")

    # Module diffs
    old_modules = old.get("modules", [])
    new_modules = new.get("modules", [])
    changes.extend(diff_modules(old_modules, new_modules))

    # Count regressions
    for line in changes:
        if "*** REGRESSION ***" in line:
            regression_count += 1

    changes.append("")
    total_changes = len([c for c in changes if c.startswith("  [")])
    changes.append(f"Summary: {total_changes} change(s), {regression_count} regression(s)")

    output = "\n".join(changes)
    print(output)

    return 1 if regression_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())

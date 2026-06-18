#!/usr/bin/env python3
"""
Compare two diagnostic metadata JSON files and print a human-readable diff.
"""

import argparse
import json
import sys
from pathlib import Path


def load_metadata(path: str) -> dict:
    """Load and validate a diagnostic metadata JSON file."""
    p = Path(path)
    if not p.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        with open(p) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)


def build_module_map(metadata: dict) -> dict[str, dict]:
    """Build a dict of module name -> module info."""
    return {m["name"]: m for m in metadata.get("modules", [])}


def diff_metadata(old: dict, new: dict) -> dict:
    """Compare two diagnostic metadata dicts and return a structured diff."""
    old_modules = build_module_map(old)
    new_modules = build_module_map(new)

    old_names = set(old_modules.keys())
    new_names = set(new_modules.keys())

    added = list(new_names - old_names)
    removed = list(old_names - new_names)
    common = old_names & new_names

    changed = []
    for name in sorted(common):
        om = old_modules[name]
        nm = new_modules[name]
        deltas = {}
        if om.get("status") != nm.get("status"):
            deltas["status"] = {"from": om.get("status"), "to": nm.get("status")}
        if om.get("elapsed_seconds") != nm.get("elapsed_seconds"):
            deltas["elapsed_seconds"] = {
                "from": om.get("elapsed_seconds"),
                "to": nm.get("elapsed_seconds"),
                "delta": (nm.get("elapsed_seconds") or 0) - (om.get("elapsed_seconds") or 0),
            }
        if om.get("command") != nm.get("command"):
            deltas["command"] = {"from": om.get("command"), "to": nm.get("command")}
        if om.get("artifact") != nm.get("artifact"):
            deltas["artifact"] = {"from": om.get("artifact"), "to": nm.get("artifact")}
        if deltas:
            changed.append({"name": name, **deltas})

    return {
        "old_file": old.get("commit", "unknown"),
        "new_file": new.get("commit", "unknown"),
        "old_total_modules": old.get("total_modules"),
        "new_total_modules": new.get("total_modules"),
        "old_passed": old.get("passed"),
        "new_passed": new.get("passed"),
        "old_failed": old.get("failed"),
        "new_failed": new.get("failed"),
        "added_modules": added,
        "removed_modules": removed,
        "changed_modules": changed,
    }


def print_human_diff(diff: dict) -> None:
    """Print a human-readable diff."""
    print(f"=== Diagnostic Metadata Diff ===")
    print(f"  Old: commit {diff['old_file']} ({diff['old_total_modules']} modules)")
    print(f"  New: commit {diff['new_file']} ({diff['new_total_modules']} modules)")
    print()

    if diff["old_passed"] != diff["new_passed"]:
        print(f"  Passed: {diff['old_passed']} -> {diff['new_passed']}")
    if diff["old_failed"] != diff["new_failed"]:
        print(f"  Failed: {diff['old_failed']} -> {diff['new_failed']}")
    print()

    if diff["added_modules"]:
        print(f"  Added modules ({len(diff['added_modules'])}):")
        for name in sorted(diff["added_modules"]):
            print(f"    + {name}")

    if diff["removed_modules"]:
        print(f"  Removed modules ({len(diff['removed_modules'])}):")
        for name in sorted(diff["removed_modules"]):
            print(f"    - {name}")

    if diff["changed_modules"]:
        print(f"  Changed modules ({len(diff['changed_modules'])}):")
        for mod in diff["changed_modules"]:
            print(f"    ~ {mod['name']}:")
            if "status" in mod:
                print(f"        status: {mod['status']['from']} -> {mod['status']['to']}")
            if "elapsed_seconds" in mod:
                delta = mod["elapsed_seconds"]["delta"]
                sign = "+" if delta >= 0 else ""
                print(f"        duration: {mod['elapsed_seconds']['from']}s -> {mod['elapsed_seconds']['to']}s ({sign}{delta}s)")
            if "command" in mod:
                print(f"        command changed")
            if "artifact" in mod:
                print(f"        artifact: {mod['artifact']['from']} -> {mod['artifact']['to']}")

    if not diff["added_modules"] and not diff["removed_modules"] and not diff["changed_modules"]:
        print("  No differences found.")


def main():
    parser = argparse.ArgumentParser(
        description="Compare two diagnostic metadata JSON files and print a diff.",
    )
    parser.add_argument("old", help="Path to the older diagnostic metadata JSON")
    parser.add_argument("new", help="Path to the newer diagnostic metadata JSON")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON diff")

    args = parser.parse_args()

    old_meta = load_metadata(args.old)
    new_meta = load_metadata(args.new)

    diff = diff_metadata(old_meta, new_meta)

    if args.json:
        print(json.dumps(diff, indent=2))
    else:
        print_human_diff(diff)


if __name__ == "__main__":
    main()

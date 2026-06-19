#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PASS_STATUSES = {"PASS", "PASSED", "SUCCESS", "OK"}
FAIL_STATUSES = {"FAIL", "FAILED", "ERROR", "ERR"}


def load_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"metadata file not found: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"metadata file is empty: {path}")

    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"metadata root must be an object: {path}")
    return data


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        flattened: dict[str, Any] = {}
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(_flatten(child, child_prefix))
        return flattened
    return {prefix: value}


def _module_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    modules = data.get("modules", [])
    if not isinstance(modules, list):
        return {}

    mapped: dict[str, dict[str, Any]] = {}
    for module in modules:
        if isinstance(module, dict) and module.get("name"):
            mapped[str(module["name"])] = module
    return mapped


def _is_regression(before: Any, after: Any) -> bool:
    before_status = str(before).upper()
    after_status = str(after).upper()
    return before_status in PASS_STATUSES and after_status in FAIL_STATUSES


def compare_metadata(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_flat = _flatten({k: v for k, v in before.items() if k != "modules"})
    after_flat = _flatten({k: v for k, v in after.items() if k != "modules"})

    added = {key: after_flat[key] for key in sorted(after_flat.keys() - before_flat.keys())}
    removed = {key: before_flat[key] for key in sorted(before_flat.keys() - after_flat.keys())}
    changed = {
        key: {"before": before_flat[key], "after": after_flat[key]}
        for key in sorted(before_flat.keys() & after_flat.keys())
        if before_flat[key] != after_flat[key]
    }

    before_modules = _module_map(before)
    after_modules = _module_map(after)
    module_changes: dict[str, Any] = {
        "added": sorted(after_modules.keys() - before_modules.keys()),
        "removed": sorted(before_modules.keys() - after_modules.keys()),
        "status": {},
        "elapsed_seconds": {},
    }
    regressions: list[dict[str, Any]] = []

    for name in sorted(before_modules.keys() & after_modules.keys()):
        old = before_modules[name]
        new = after_modules[name]
        old_status = old.get("status")
        new_status = new.get("status")
        if old_status != new_status:
            module_changes["status"][name] = {"before": old_status, "after": new_status}
            if _is_regression(old_status, new_status):
                regressions.append(
                    {
                        "module": name,
                        "type": "status",
                        "before": old_status,
                        "after": new_status,
                    }
                )

        old_elapsed = old.get("elapsed_seconds")
        new_elapsed = new.get("elapsed_seconds")
        if old_elapsed != new_elapsed:
            module_changes["elapsed_seconds"][name] = {
                "before": old_elapsed,
                "after": new_elapsed,
                "delta": _numeric_delta(old_elapsed, new_elapsed),
            }

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "modules": module_changes,
        "regressions": regressions,
        "has_regressions": bool(regressions),
    }


def _numeric_delta(before: Any, after: Any) -> float | None:
    try:
        return round(float(after) - float(before), 3)
    except (TypeError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare two diagnostic build metadata JSON files."
    )
    parser.add_argument("before", type=Path, help="Earlier diagnostic/build-*.json")
    parser.add_argument("after", type=Path, help="Later diagnostic/build-*.json")
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the structured JSON diff.",
    )
    args = parser.parse_args(argv)

    try:
        diff = compare_metadata(load_metadata(args.before), load_metadata(args.after))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"diagnostic diff error: {exc}", file=sys.stderr)
        return 2

    indent = 2 if args.pretty else None
    print(json.dumps(diff, indent=indent, sort_keys=True))
    return 1 if diff["has_regressions"] else 0


if __name__ == "__main__":
    sys.exit(main())

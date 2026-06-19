import argparse
import json
import sys

def load_json(filepath):
    if not filepath:
        return {}
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {filepath}")
        sys.exit(1)

def diff_metadata(old_data, new_data):
    added = set(new_data.keys()) - set(old_data.keys())
    removed = set(old_data.keys()) - set(new_data.keys())
    changed = {}
    
    for key in set(old_data.keys()) & set(new_data.keys()):
        if key == "modules":
            continue
        if old_data[key] != new_data[key]:
            changed[key] = {"old": old_data[key], "new": new_data[key]}
            
    return {"added": list(added), "removed": list(removed), "changed": changed}

def diff_modules(old_modules, new_modules):
    old_mod_dict = {m.get("name"): m for m in old_modules if m.get("name")}
    new_mod_dict = {m.get("name"): m for m in new_modules if m.get("name")}
    
    status_changes = {}
    time_changes = {}
    regressions = False

    all_names = set(old_mod_dict.keys()) | set(new_mod_dict.keys())
    
    for name in all_names:
        old_m = old_mod_dict.get(name, {})
        new_m = new_mod_dict.get(name, {})
        
        old_status = old_m.get("status", "UNKNOWN")
        new_status = new_m.get("status", "UNKNOWN")
        
        if old_status != new_status:
            status_changes[name] = {"old": old_status, "new": new_status}
            if new_status == "FAIL":
                regressions = True
                
        old_time = old_m.get("elapsed_seconds", 0)
        new_time = new_m.get("elapsed_seconds", 0)
        time_changes[name] = {"old": old_time, "new": new_time, "diff": new_time - old_time}

    return {"status_changes": status_changes, "time_changes": time_changes, "regressions": regressions}

def print_diff(meta_diff, mod_diff):
    print("=== Metadata Changes ===")
    if meta_diff["added"]:
        print(f"Added fields: {', '.join(meta_diff['added'])}")
    if meta_diff["removed"]:
        print(f"Removed fields: {', '.join(meta_diff['removed'])}")
    if meta_diff["changed"]:
        print("Changed fields:")
        for k, v in meta_diff["changed"].items():
            print(f"  {k}: {v['old']} -> {v['new']}")
            
    print("\n=== Module Status Changes ===")
    if mod_diff["status_changes"]:
        for name, statuses in mod_diff["status_changes"].items():
            arrow = "->"
            old = statuses["old"]
            new = statuses["new"]
            print(f"  {name}: {old} {arrow} {new}")
    else:
        print("  No status changes.")
        
    print("\n=== Module Time Changes ===")
    for name, times in mod_diff["time_changes"].items():
        print(f"  {name}: {times['old']}s -> {times['new']}s (diff: {times['diff']}s)")

def main():
    parser = argparse.ArgumentParser(description="Diagnostic metadata diff tool")
    parser.add_argument("old_json", help="Path to the old diagnostic JSON")
    parser.add_argument("new_json", help="Path to the new diagnostic JSON")
    args = parser.parse_args()

    old_data = load_json(args.old_json)
    new_data = load_json(args.new_json)

    if not old_data and not new_data:
        print("Empty input provided.")
        sys.exit(0)

    meta_diff = diff_metadata(old_data, new_data)
    old_modules = old_data.get("modules", [])
    new_modules = new_data.get("modules", [])
    
    mod_diff = diff_modules(old_modules, new_modules)
    
    print_diff(meta_diff, mod_diff)
    
    if mod_diff["regressions"]:
        print("\n[!] Regressions detected. Exiting with non-zero code.")
        sys.exit(1)

if __name__ == "__main__":
    main()

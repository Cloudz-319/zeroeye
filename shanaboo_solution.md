 ```diff
--- a/build.py
+++ b/build.py
@@ -1,4 +1,5 @@
 #!/usr/bin/env python3
+# -*- coding: utf-8 -*-
 
 import argparse
 import datetime
@@ -12,6 +13,7 @@
 import time
 from dataclasses import dataclass
 from pathlib import Path
+from typing import Any
 from typing import Callable, Optional
 
 ROOT = Path(__file__).resolve().parent
@@ -23,6 +25,7 @@
 ENCRYPTLY_PACK_INITIAL_BACKOFF_SECONDS = 0.5
 ENCRYPTLY_PACK_MAX_BACKOFF_SECONDS = 5.0
 
+DIAGNOSTIC_JSON_SUFFIX = "-metadata"
 
 def current_commit_id() -> str:
     """Return the first 4 bytes (8 hex chars) of HEAD for stable per-commit diagnostics."""
@@ -42,7 +45,7 @@
 def diagnostic_paths_for_commit() -> tuple[Path, Path, str]:
     """Return stable diagnostic artifact paths under diagnostic/ for the current commit."""
     DIAGNOSTIC_DIR.mkdir(parents=True, exist_ok=True)
     commit_id = current_commit_id()
     logd_path = DIAGNOSTIC_DIR / f"build-{commit_id}.logd"
-    metadata_path = DIAGNOSTIC_DIR / f"build-{commit_id}.json"
+    metadata_path = DIAGNOSTIC_DIR / f"build-{commit_id}{DIAGNOSTIC_JSON_SUFFIX}.json"
     return logd_path, metadata_path, commit_id
 
 
@@ -73,6 +76,7 @@
     retry_errors: Optional[list[str]] = None
 
 MODULES = [
+    # ... existing modules ...
     Module(
         name="backend",
         language="Rust",
@@ -130,6 +134,7 @@
         build_dir=ROOT / "frailbox" / "engine" / "build" / "trial-engine",
         env={"JAVA_HOME": os.environ.get("JAVA_HOME", "/usr/lib/jvm/java-21-openjdk-amd64")},
     ),
+    # ... rest of modules ...
 ]
 
 def run_encryptly_pack(logd_path: Path) -> EncryptlyPackResult:
@@ -235,6 +240,7 @@
     parser.add_argument("--clean", action="store_true", help="Clean all artifacts")
     parser.add_argument("--module", type=str, help="Comma-separated list of modules to build")
     parser.add_argument("--release", action="store_true", help="Release mode (Rust only)")
+    parser.add_argument("--compare-diagnostics", nargs=2, metavar=("OLD", "NEW"), help="Compare two diagnostic metadata JSON files")
     args = parser.parse_args()
 
     if args.clean:
@@ -244,6 +250,10 @@
             module.clean()
         sys.exit(0)
 
+    if args.compare_diagnostics:
+        result = compare_diagnostics(Path(args.compare_diagnostics[0]), Path(args.compare_diagnostics[1]))
+        sys.exit(result)
+
     selected_modules = MODULES
     if args.module:
         names = {m.strip() for m in args.module.split(",")}
@@ -287,5 +296,189 @@
         print(f"Diagnostic metadata: {metadata_path}")
 
 
+def load_diagnostic_json(path: Path) -> dict[str, Any]:
+    """Load and validate a diagnostic metadata JSON file."""
+    if not path.exists():
+        raise FileNotFoundError(f"Diagnostic file not found: {path}")
+    with open(path, "r", encoding="utf-8") as f:
+        data = json.load(f)
+    if not isinstance(data, dict):
+        raise ValueError(f"Expected JSON object in {path}")
+    return data
+
+
+def compare_module_results(old_results: dict[str, Any], new_results: dict[str, Any]) -> dict[str, Any]:
+    """Compare module results between two builds and return structured diff."""
+    diff: dict[str, Any] = {
+        "added": {},
+        "removed": {},
+        "changed": {},
+        "unchanged": {},
+    }
+
+    old_modules = set(old_results.keys())
+    new_modules = set(new_results.keys())
+
+    # Added modules
+    for module in new_modules - old_modules:
+        diff["added"][module] = new_results[module]
+
+    # Removed modules
+    for module in old_modules - new_modules:
+        diff["removed"][module] = old_results[module]
+
+    # Changed and unchanged modules
+    for module in old_modules & new_modules:
+        old_data = old_results[module]
+        new_data = new_results[module]
+
+        if old_data == new_data:
+            diff["unchanged"][module] = old_data
+        else:
+            module_diff: dict[str, Any] = {}
+
+            # Status change
+            old_status = old_data.get("status") if isinstance(old_data, dict) else None
+            new_status = new_data.get("status") if isinstance(new_data, dict) else None
+            if old_status != new_status:
+                module_diff["status"] = {
+                    "old": old_status,
+                    "new": new_status,
+                    "regression": (old_status == "PASS" and new_status == "FAIL"),
+                    "improvement": (old_status == "FAIL" and new_status == "PASS"),
+                }
+
+            # Elapsed time change
+            old_elapsed = old_data.get("elapsed_seconds") if isinstance(old_data, dict) else None
+            new_elapsed = new_data.get("elapsed_seconds") if isinstance(new_data, dict) else None
+            if old_elapsed != new_elapsed and old_elapsed is not None and new_elapsed is not None:
+                try:
+                    old_val = float(old_elapsed)
+                    new_val = float(new_elapsed)
+                    module_diff["elapsed_seconds"] = {
+                        "old": old_val,
+                        "new": new_val,
+                        "delta": round(new_val - old_val, 4),
+                        "slower": new_val > old_val,
+                    }
+                except (ValueError, TypeError):
+                    module_diff["elapsed_seconds"] = {"old": old_elapsed, "new": new_elapsed}
+            elif old_elapsed != new_elapsed:
+                module_diff["elapsed_seconds"] = {"old": old_elapsed, "new": new_elapsed}
+
+            # Other field changes
+            if isinstance(old_data, dict) and isinstance(new_data, dict):
+                all_keys = set(old_data.keys()) | | set(new_data.keys())
+                other_changes = {}
+                for key in all_keys:
+                    if key in ("status", "elapsed_seconds"):
+                        continue
+                    old_val = old_data.get(key)
+                    new_val = new_data.get(key)
+                    if old_val != new_val:
+                        other_changes[key] = {"old": old_val, "new": new_val
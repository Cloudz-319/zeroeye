 ```diff
--- a/build.py
+++ b/build.py
@@ -1,4 +1,5 @@
 #!/usr/bin/env python3
+"""Build script for Tent of Trials with diagnostic metadata generation and comparison."""
 
 import argparse
 import datetime
@@ -10,6 +11,7 @@
 import subprocess
 import sys
 import time
+from collections.abc import Sequence
 from dataclasses import dataclass
 from pathlib import Path
 from typing import Callable, Optional
@@ -18,6 +20,7 @@
 DIAGNOSTIC_DIR = ROOT / "diagnostic"
 DIAGNOSTIC_CHUNK_SIZE = 40 * 1024 * 1024
 ENCRYPTLY_BLOCKER_MESSAGE = "You need to fix your environment so encryptly runs before building."
+ENCRYPTLY_BLOCKER_EXIT_CODE = 3
 ENCRYPTLY_PACK_MAX_ATTEMPTS = 3
 ENCRYPTLY_PACK_INITIAL_BACKOFF_SECONDS = 0.5
 ENCRYPTLY_PACK_MAX_BACKOFF_SECONDS = 5.0
@@ -56,6 +59,7 @@
     retry_errors: Optional[list[str]] = None
 
 MODULES = [
+    # fmt: off
     Module(
         name="backend",
         language="Rust",
@@ -106,6 +110,7 @@
         clean_cmd=["rm", "-rf", "build"],
         build_dir=ROOT / "frailbox" / "engine" / "build" / "trial-engine",
     ),
+    # fmt: on
 ]
 
 
@@ -118,6 +123,7 @@
     retry_errors: Optional[list[str]] = None
 
 
+def _encryptly_bin() -> str:
     """Return the path to the encryptly binary, or raise RuntimeError."""
     encryptly_path = shutil.which("encryptly")
     if not encryptly_path:
@@ -125,6 +131,7 @@
     return encryptly_path
 
 
+def _generate_password(length: int = 32) -> str:
     """Generate a random alphanumeric password."""
     import random
     import string
@@ -133,6 +140,7 @@
     return "".join(random.choices(chars, k=length))
 
 
+def encryptly_pack(logd_path: Path, password: str) -> EncryptlyPackResult:
     """Pack a .logd file using encryptly with retry logic."""
     import time as _time
 
@@ -181,6 +189,7 @@
     )
 
 
+def encryptly_unpack(logd_path: Path, password: str, out_path: Path) -> bool:
     """Unpack a .logd file using encryptly. Returns True on success."""
     if not logd_path.exists():
         return False
@@ -196,6 +205,7 @@
         return False
 
 
+def run_module_build(module: Module, args: argparse.Namespace) -> dict:
     """Build a single module and return its diagnostic metadata."""
     print(f"[build] {module.name} ({module.language})")
     start = time.time()
@@ -232,6 +242,7 @@
     }
 
 
+def run_module_clean(module: Module) -> None:
     """Clean a single module's build artifacts."""
     print(f"[clean] {module.name}")
     try:
@@ -242,6 +253,7 @@
         print(f"  Error during clean: {e}")
 
 
+def write_diagnostic_metadata(metadata: dict, metadata_path: Path) -> None:
     """Write diagnostic metadata to a JSON file."""
     with open(metadata_path, "w") as f:
         json.dump(metadata, f, indent=2)
@@ -249,6 +261,7 @@
     print(f"[diagnostic] Metadata written to {metadata_path}")
 
 
+def generate_diagnostic_report(results: list[dict], metadata_path: Path) -> None:
     """Generate and write the diagnostic report."""
     metadata = {
         "timestamp": datetime.datetime.now().isoformat(),
@@ -261,6 +274,7 @@
     write_diagnostic_metadata(metadata, metadata_path)
 
 
+def build_all(args: argparse.Namespace) -> tuple[list[dict], Path, Path, str]:
     """Build all modules and generate diagnostics. Returns results and paths."""
     logd_path, metadata_path, commit_id = diagnostic_paths_for_commit()
 
@@ -287,6 +301,7 @@
     return results, logd_path, metadata_path, commit_id
 
 
+def clean_all() -> None:
     """Clean all module build artifacts."""
     for module in MODULES:
         run_module_clean(module)
@@ -295,6 +310,7 @@
     print("[clean] Done.")
 
 
+def parse_args() -> argparse.Namespace:
     parser = argparse.ArgumentParser(description="Tent of Trials build script")
     parser.add_argument("--clean", action="store_true", help="Clean all build artifacts")
     parser.add_argument("--module", type=str, help="Comma-separated list of modules to build")
@@ -304,6 +320,7 @@
     return parser.parse_args()
 
 
+def main() -> int:
     args = parse_args()
 
     if args.clean:
@@ -323,5 +340,6 @@
     return 0
 
 
+if __name__ == "__main__":
     sys.exit(main())
 
--- /dev/null
+++ b/diagnostic/diff.py
@@ -0,0 +1,328 @@
+#!/usr/bin/env python3
+"""Diagnostic metadata comparison tool for Tent of Trials builds.
+
+Accepts two diagnostic metadata JSON files and produces a structured diff
+showing which fields changed between builds, highlighting regressions and
+improvements.
+"""
+
+from __future__ import annotations
+
+import argparse
+import json
+import sys
+from dataclasses import dataclass, field
+from pathlib import Path
+from typing import Any
+
+
+@dataclass
+class ModuleDiff:
+    """Diff result for a single module."""
+
+    name: str
+    old_status: str | None = None
+    new_status: str | None = None
+    old_elapsed: float | None = None
+    new_elapsed: float | None = None
+    status_changed: bool = False
+    elapsed_changed: bool = False
+    is_regression: bool = False
+    is_improvement: bool = False
+
+
+@dataclass
+class BuildDiff:
+    """Overall diff result between two builds."""
+
+    old_file: str
+    new_file: str
+    added_modules: list[str] = field(default_factory=list)
+    removed_modules: list[str] = field(default_factory=list)
+    changed_modules: list[ModuleDiff] = field(default_factory=list)
+    unchanged_modules: list[str] = field(default_factory=list)
+    regressions: list[str] = field(default_factory=list)
+    improvements: list[str] = field(default_factory=list)
+
+
+def _load_json(path: Path) -> dict[str, Any]:
+    """Load and validate a diagnostic metadata JSON file."""
+   
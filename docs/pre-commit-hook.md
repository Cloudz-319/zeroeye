# Pre-commit Hook

This document describes the pre-commit hook that automates diagnostic build generation.

## Overview

Every PR to this repository must include diagnostic build artifacts (`diagnostic/build-*.logd` and `diagnostic/build-*.json`). The pre-commit hook automates this process so you don't have to manually run `build.py` and copy files before every commit.

## Installation

```bash
make install-hooks
```

This copies `tools/pre-commit` into `.git/hooks/pre-commit` and makes it executable.

## What It Does

When you run `git commit`, the hook will:

1. **Check for cached diagnostics** — If the diagnostic files are already staged and unchanged since the last build, the hook skips the rebuild entirely (fast path).

2. **Countdown** — Prints a 3-second countdown before starting the build (because `build.py` takes a while).

3. **Run `python3 build.py`** — Executes the full build pipeline.

4. **Find artifacts** — Locates the most recent `diagnostic/build-*.logd` and `diagnostic/build-*.json` files.

5. **Stage artifacts** — Automatically `git add`s the diagnostic files so they're included in the commit.

6. **Cache hashes** — Stores file hashes in `.git/.diagnostic-hashes` to detect changes on subsequent commits.

## Uninstallation

```bash
make uninstall-hooks
```

## Cache Management

To clear the diagnostic hash cache (forces a rebuild on next commit):

```bash
make clean-diagnostics
```

## Manual Usage

You can also run the hook manually without committing:

```bash
python3 tools/pre-commit
```

## Troubleshooting

### Build fails during commit

If `build.py` fails, the hook prints the error output and aborts the commit. Fix the build errors and try again.

### Hook doesn't run

Ensure the hook is installed:

```bash
ls -la .git/hooks/pre-commit
```

If missing, run `make install-hooks`.

### Diagnostic files not staged

If the hook runs but diagnostic files aren't staged, check that `diagnostic/` exists and `build.py` produces output there.

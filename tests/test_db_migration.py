"""Tests for tools/db_migration.py."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))


def test_imports():
    import db_migration  # noqa
    assert True


def test_has_main():
    import db_migration
    assert hasattr(db_migration, "main")
    assert callable(db_migration.main)


def test_has_main():
    import db_migration
    assert hasattr(db_migration, "main")
    assert callable(db_migration.main)


def test_execute_sql_has_valid_params():
    import db_migration
    import inspect
    sig = inspect.signature(db_migration.execute_sql)
    params = list(sig.parameters.keys())
    assert "sql" in params
    assert "db_config" in params


def test_apply_migration_has_valid_params():
    import db_migration
    import inspect
    sig = inspect.signature(db_migration.apply_migration)
    params = list(sig.parameters.keys())
    assert "version" in params
    assert "direction" in params


def test_get_migration_status_exists():
    import db_migration
    result = db_migration.get_migration_status()
    assert isinstance(result, list)


def test_run_all_migrations_has_dry_run_param():
    import db_migration
    import inspect
    sig = inspect.signature(db_migration.run_all_migrations)
    assert "dry_run" in sig.parameters


def test_create_migration_has_description_param():
    import db_migration
    import inspect
    sig = inspect.signature(db_migration.create_migration)
    assert "description" in sig.parameters

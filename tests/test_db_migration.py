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


def test_parse_args_defaults():
    import db_migration
    args = db_migration.parse_args(["--action", "up"])
    assert args.action == "up"


def test_parse_args_down():
    import db_migration
    args = db_migration.parse_args(["--action", "down"])
    assert args.action == "down"


def test_parse_args_create():
    import db_migration
    args = db_migration.parse_args(["--action", "create", "--name", "add_users"])
    assert args.action == "create"
    assert args.name == "add_users"


def test_parse_args_invalid_action():
    import db_migration
    with pytest.raises(SystemExit):
        db_migration.parse_args(["--action", "invalid"])


def test_schema_version_int():
    import db_migration
    version = db_migration.parse_schema_version("001_initial")
    assert version == 1


def test_schema_version_no_prefix():
    import db_migration
    with pytest.raises(ValueError):
        db_migration.parse_schema_version("initial")

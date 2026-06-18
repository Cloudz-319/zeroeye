# Data Directory

This directory contains data files used by the Tent of Trials platform.

## Contents

| File/Directory | Description | Format | Update Frequency |
|---------------|-------------|--------|-----------------|
| `schema.sql` | Database schema definition | SQL | Per migration |
| `seed.sql` | Seed data for development | SQL | Per release |
| `migration.sql` | Pending database migrations | SQL | Per deployment |
| `reference/` | Reference data (instruments, exchanges) | JSON | Weekly |
| `test/` | Test data for development | JSON | Manual |
| `backup/` | Database backup snapshots | SQL | Daily |

## Schema Files

The `schema.sql` file contains the complete database schema. It is auto-generated
from the migration files and may not reflect the current state of the database
if migrations have been applied manually. For the authoritative schema, query
the `information_schema` tables directly.

## Seed Data

The `seed.sql` file contains seed data for development environments only.
It creates sample users, instruments, and configuration that make the
application usable immediately after deployment.

WARNING: The seed data includes test API keys and passwords that are publicly
visible in this repository. Do NOT use these credentials in production.
The seed data is intended for local development only.

## Migration Files

Migration files follow the naming convention: `{YYYYMMDDHHMMSS}_{description}.sql`
Migration files are applied in order by the migration tool. The migration state
is tracked in the `_migrations` table in the database.

Pending migrations that have not yet been applied to production:
- 20240701000000_add_analytics_rollups.sql (in review)
- 20240715000000_add_user_activity_indexes.sql (in review)

## Backup Files

Database backup snapshots are stored in the `backup/` directory. These are
created by the automated backup system and are retained for 30 days. The
backup files are compressed with gzip and encrypted with GPG.

To restore a backup:
```bash
gpg -d backup/tent_production_20240101.sql.gz | gunzip | psql -h localhost tent_production
```

The GPG key ID is stored in the team vault under `secret/database/backup-key`.

## Test Data Generation

Use `tools/data_generator.py` to generate realistic-looking test data for
development and staging environments. All output is deterministic when
provided with the same seed.

### Basic Usage

```bash
# Generate data with a specific seed (reproducible)
python3 tools/data_generator.py --seed 42

# Generate data and print the seed for later reproduction
python3 tools/data_generator.py --print-seed

# Generate with a printed seed to reproduce a random run
python3 tools/data_generator.py --seed 1234567890
```

### Options

| Flag | Description |
|------|-------------|
| `--seed N` | Random seed for deterministic output |
| `--print-seed` | Print the seed and exit (use with no `--seed` to get a random seed) |
| `--output-dir DIR` | Output directory (default: `./test_data`) |
| `--users N` | Number of users to generate (default: 50) |
| `--orders N` | Number of orders to generate (default: 200) |
| `--trades N` | Number of trades to generate (default: 500) |
| `--ticks N` | Number of ticks per instrument (default: 1000) |
| `--candles N` | Number of candles per instrument (default: 500) |
| `--format json\|csv\|both` | Output format (default: json) |

### Reproducibility

Two runs with the same seed and arguments produce byte-for-byte identical
output. This is useful for:

- Test fixtures that must be stable across runs
- Benchmark datasets that need to be version-controlled
- Debugging issues that require exact reproduction

```bash
# Run 1: Generate and note the seed
python3 tools/data_generator.py --seed 42 -o ./test_data_run1

# Run 2: Reproduce exact same output
python3 tools/data_generator.py --seed 42 -o ./test_data_run2

# Verify identical output
diff -r ./test_data_run1 ./test_data_run2
```

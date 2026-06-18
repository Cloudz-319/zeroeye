"""Tests for JSONL and text output formats in log aggregator (issue #185)."""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from log_aggregator import LogAggregator


class TestJSONLOutput:
    """JSONL output format must produce valid JSONL with required fields."""

    def test_jsonl_has_required_fields(self):
        """Each JSONL record must have timestamp/level/source/message/metadata."""
        aggregator = LogAggregator()
        aggregator._parse_line(
            '{"timestamp": 1705312200, "level": "ERROR", '
            '"service": "api", "message": "connection timeout"}'
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            output_path = f.name

        try:
            aggregator.export_jsonl(output_path)
            with open(output_path) as f:
                records = [json.loads(line) for line in f]

            assert len(records) == 1
            record = records[0]
            assert "timestamp" in record
            assert "level" in record
            assert "source" in record
            assert "message" in record
            assert "metadata" in record
        finally:
            os.unlink(output_path)

    def test_jsonl_source_maps_from_service(self):
        """JSONL 'source' field must map from the parsed 'service' field."""
        aggregator = LogAggregator()
        aggregator._parse_line(
            '{"timestamp": 1705312200, "level": "INFO", '
            '"service": "auth-service", "message": "user created"}'
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            output_path = f.name

        try:
            aggregator.export_jsonl(output_path)
            with open(output_path) as f:
                record = json.loads(f.readline())

            assert record["source"] == "auth-service"
        finally:
            os.unlink(output_path)

    def test_jsonl_preserves_parse_order(self):
        """JSONL output must preserve the order entries were parsed."""
        aggregator = LogAggregator()
        lines = [
            '{"timestamp": 1705312200, "level": "INFO", "service": "api", "message": "first entry"}',
            '{"timestamp": 1705312260, "level": "ERROR", "service": "web", "message": "second entry"}',
            '{"timestamp": 1705312320, "level": "WARN", "service": "db", "message": "third entry"}',
        ]
        for line in lines:
            aggregator._parse_line(line)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            output_path = f.name

        try:
            aggregator.export_jsonl(output_path)
            with open(output_path) as f:
                messages = [json.loads(line)["message"] for line in f]

            assert messages == ["first entry", "second entry", "third entry"]
        finally:
            os.unlink(output_path)

    def test_jsonl_metadata_contains_extra_fields(self):
        """JSONL metadata should contain the full parsed entry beyond the five core fields."""
        aggregator = LogAggregator()
        aggregator._parse_line(
            '{"timestamp": 1705312200, "level": "ERROR", '
            '"service": "api", "message": "crash", "trace_id": "abc123"}'
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            output_path = f.name

        try:
            aggregator.export_jsonl(output_path)
            with open(output_path) as f:
                record = json.loads(f.readline())

            assert isinstance(record["metadata"], dict)
            assert record["metadata"].get("fields", {}).get("trace_id") == "abc123"
        finally:
            os.unlink(output_path)

    def test_jsonl_empty_entries(self):
        """JSONL export with no entries should produce an empty file."""
        aggregator = LogAggregator()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            output_path = f.name

        try:
            aggregator.export_jsonl(output_path)
            with open(output_path) as f:
                content = f.read()
            assert content == ""
        finally:
            os.unlink(output_path)

    def test_jsonl_plain_text_input(self):
        """JSONL must work with plain text parsed entries too."""
        aggregator = LogAggregator()
        aggregator._parse_line("2024-06-18T12:00:00 [worker] ERROR: job failed")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            output_path = f.name

        try:
            aggregator.export_jsonl(output_path)
            with open(output_path) as f:
                record = json.loads(f.readline())

            assert "timestamp" in record
            assert record["level"] == "error"
            assert record["source"] == "worker"
            assert "job failed" in record["message"]
        finally:
            os.unlink(output_path)


class TestTextOutput:
    """Text output format must produce human-readable plain text."""

    def test_text_output_basic(self):
        """Text export should produce one line per entry."""
        aggregator = LogAggregator()
        aggregator._parse_line(
            '{"timestamp": 1705312200, "level": "INFO", '
            '"service": "api", "message": "startup"}'
        )
        aggregator._parse_line(
            '{"timestamp": 1705312260, "level": "ERROR", '
            '"service": "web", "message": "timeout"}'
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            output_path = f.name

        try:
            aggregator.export_text(output_path)
            with open(output_path) as f:
                lines = f.readlines()

            assert len(lines) == 2
        finally:
            os.unlink(output_path)

    def test_text_empty(self):
        """Text export with no entries should produce an empty file."""
        aggregator = LogAggregator()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            output_path = f.name

        try:
            aggregator.export_text(output_path)
            with open(output_path) as f:
                content = f.read()
            assert content == ""
        finally:
            os.unlink(output_path)


class TestCLIFormat:
    """CLI --format flag must accept text and jsonl."""

    def test_cli_help_includes_jsonl(self):
        """--help output should mention jsonl as a format choice."""
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "..", "tools", "log_aggregator.py"),
             "--help"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "jsonl" in result.stdout or "jsonl" in result.stderr

    def test_cli_help_includes_text(self):
        """--help output should mention text as a format choice."""
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "..", "tools", "log_aggregator.py"),
             "--help"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "text" in result.stdout or "text" in result.stderr

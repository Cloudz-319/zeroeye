# Fix for Issue #10: [$25 BOUNTY] [Python] Add JSONL output format to log aggregator

#!/usr/bin/env python3
"""
Log Aggregator for ZeroEye
Aggregates and formats logs from various sources with support for multiple output formats.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, TextIO


class LogEntry:
    """Represents a single log entry with structured fields."""
    
    def __init__(
        self,
        timestamp: str,
        level: str,
        module: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.timestamp = timestamp
        self.level = level.upper()
        self.module = module
        self.message = message
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary representation."""
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "module": self.module,
            "message": self.message,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """Convert log entry to JSON string with proper escaping."""
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(',', ':'))
    
    def to_plain_text(self) -> str:
        """Convert log entry to plain text format."""
        meta_str = ""
        if self.metadata:
            meta_parts = [f"{k}={v}" for k, v in self.metadata.items()]
            meta_str = f" [{', '.join(meta_parts)}]"
        return f"[{self.timestamp}] [{self.level}] [{self.module}] {self.message}{meta_str}"


class LogParser:
    """Parses log lines into structured LogEntry objects."""
    
    # Common log patterns
    PATTERNS = [
        # Pattern: [timestamp] [LEVEL] [module] message
        re.compile(
            r'\[(?P<timestamp>[^\]]+)\]\s*\[(?P<level>\w+)\]\s*\[(?P<module>[^\]]+)\]\s*(?P<message>.+)',
            re.DOTALL
        ),
        # Pattern: timestamp LEVEL module: message
        re.compile(
            r'(?P<timestamp>\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+'
            r'(?P<level>\w+)\s+(?P<module>[\w.]+):\s*(?P<message>.+)',
            re.DOTALL
        ),
        # Pattern: LEVEL [timestamp] module - message
        re.compile(
            r'(?P<level>\w+)\s+\[(?P<timestamp>[^\]]+)\]\s+(?P<module>[\w.]+)\s*-\s*(?P<message>.+)',
            re.DOTALL
        ),
    ]
    
    # Metadata extraction pattern
    METADATA_PATTERN = re.compile(r'(\w+)=("[^"]*"|\S+)')
    
    @classmethod
    def parse_line(cls, line: str, default_module: str = "unknown") -> Optional[LogEntry]:
        """Parse a single log line into a LogEntry."""
        line = line.strip()
        if not line:
            return None
        
        for pattern in cls.PATTERNS:
            match = pattern.match(line)
            if match:
                groups = match.groupdict()
                message = groups.get('message', '').strip()
                
                # Extract metadata from message if present
                metadata = {}
                meta_matches = cls.METADATA_PATTERN.findall(message)
                for key, value in meta_matches:
                    # Remove quotes from value if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    metadata[key] = value
                
                return LogEntry(
                    timestamp=groups.get('timestamp', datetime.utcnow().isoformat()),
                    level=groups.get('level', 'INFO'),
                    module=groups.get('module', default_module),
                    message=message,
                    metadata=metadata if metadata else None
                )
        
        # Fallback: treat entire line as message
        return LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level="INFO",
            module=default_module,
            message=line
        )


class LogAggregator:
    """Aggregates logs from multiple sources and outputs in various formats."""
    
    SUPPORTED_FORMATS = ['plain', 'jsonl']
    
    def __init__(self, output_format: str = 'plain'):
        if output_format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {output_format}. Supported: {self.SUPPORTED_FORMATS}")
        self.output_format = output_format
        self.entries: List[LogEntry] = []
    
    def add_entry(self, entry: LogEntry) -> None:
        """Add a log entry to the aggregator."""
        self.entries.append(entry)
    
    def parse_and_add(self, line: str, default_module: str = "unknown") -> Optional[LogEntry]:
        """Parse a log line and add it to the aggregator."""
        entry = LogParser.parse_line(line, default_module)
        if entry:
            self.add_entry(entry)
        return entry
    
    def parse_multiline(self, content: str, default_module: str = "unknown") -> List[LogEntry]:
        """
        Parse multiline content, handling multiline log messages properly.
        Lines that don't match a log pattern are appended to the previous entry.
        """
        lines = content.split('\n')
        entries = []
        current_entry = None
        
        for line in lines:
            if not line.strip():
                continue
            
            # Try to parse as a new log entry
            parsed = LogParser.parse_line(line, default_module)
            
            if parsed and self._looks_like_new_entry(line):
                if current_entry:
                    entries.append(current_entry)
                current_entry = parsed
            elif current_entry:
                # Append to current entry's message (multiline handling)
                current_entry.message += '\n' + line.strip()
            else:
                # First line doesn't match pattern, create entry anyway
                current_entry = parsed or LogEntry(
                    timestamp=datetime.utcnow().isoformat(),
                    level="INFO",
                    module=default_module,
                    message=line.strip()
                )
        
        if current_entry:
            entries.append(current_entry)
        
        for entry in entries:
            self.add_entry(entry)
        
        return entries
    
    def _looks_like_new_entry(self, line: str) -> bool:
        """Check if a line looks like the start of a new log entry."""
        # Check for common log entry starters
        patterns = [
            r'^\[',  # Starts with bracket
            r'^\d{4}-\d{2}-\d{2}',  # Starts with date
            r'^(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\s',  # Starts with level
        ]
        return any(re.match(p, line.strip(), re.IGNORECASE) for p in patterns)
    
    def format_entry(self, entry: LogEntry) -> str:
        """Format a single entry according to the output format."""
        if self.output_format == 'jsonl':
            return entry.to_json()
        return entry.to_plain_text()
    
    def format_all(self) -> str:
        """Format all entries and return as a single string."""
        return '\n'.join(self.format_entry(e) for e in self.entries)
    
    def stream_entries(self) -> Generator[str, None, None]:
        """Yield formatted entries one at a time."""
        for entry in self.entries:
            yield self.format_entry(entry)
    
    def write_to(self, output: TextIO) -> int:
        """Write all formatted entries to a file-like object. Returns count written."""
        count = 0
        for entry in self.entries:
            output.write(self.format_entry(entry) + '\n')
            count += 1
        return count
    
    def clear(self) -> None:
        """Clear all stored entries."""
        self.entries.clear()


def aggregate_from_file(
    filepath: str,
    output_format: str = 'plain',
    default_module: Optional[str] = None
) -> LogAggregator:
    """
    Aggregate logs from a file.
    
    Args:
        filepath: Path to the log file
        output_format: Output format ('plain' or 'jsonl')
        default_module: Default module name for entries without one
    
    Returns:
        LogAggregator with parsed entries
    """
    if default_module is None:
        # Use filename as default module
        default_module = filepath.rsplit('/', 1)[-1].rsplit('.', 1)[0]
    
    aggregator = LogAggregator(output_format=output_format)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    aggregator.parse_multiline(content, default_module)
    return aggregator


def aggregate_from_stdin(
    output_format: str = 'plain',
    default_module: str = "stdin"
) -> LogAggregator:
    """
    Aggregate logs from stdin.
    
    Args:
        output_format: Output format ('plain' or 'jsonl')
        default_module: Default module name
    
    Returns:
        LogAggregator with parsed entries
    """
    aggregator = LogAggregator(output_format=output_format)
    content = sys.stdin.read()
    aggregator.parse_multiline(content, default_module)
    return aggregator


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description='Aggregate and format logs from various sources.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --format jsonl access.log error.log
  %(prog)s --format plain -o combined.log *.log
  cat app.log | %(prog)s --format jsonl
        """
    )
    
    parser.add_argument(
        'files',
        nargs='*',
        help='Log files to aggregate (reads from stdin if none provided)'
    )
    
    parser.add_argument(
        '--format', '-f',
        choices=['plain', 'jsonl'],
        default='plain',
        help='Output format (default: plain)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output file (default: stdout)'
    )
    
    parser.add_argument(
        '--module', '-m',
        help='Default module name for log entries'
    )
    
    args = parser.parse_args()
    
    # Create aggregator with specified format
    aggregator = LogAggregator(output_format=args.format)
    
    if args.files:
        # Process each file
        for filepath in args.files:
            try:
                default_module = args.module or filepath.rsplit('/', 1)[-1].rsplit('.', 1)[0]
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                aggregator.parse_multiline(content, default_module)
            except FileNotFoundError:
                print(f"Error: File not found: {filepath}", file=sys.stderr)
                sys.exit(1)
            except PermissionError:
                print(f"Error: Permission denied: {filepath}", file=sys.stderr)
                sys.exit(1)
    else:
        # Read from stdin
        if sys.stdin.isatty():
            parser.print_help()
            sys.exit(0)
        content = sys.stdin.read()
        aggregator.parse_multiline(content, args.module or "stdin")
    
    # Output results
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            aggregator.write_to(f)
    else:
        aggregator.write_to(sys.stdout)


if __name__ == '__main__':
    main()
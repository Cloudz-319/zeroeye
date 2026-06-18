#!/usr/bin/env python3
"""
Tests for health_check.py
"""

import json
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add the tools directory to the path
sys.path.insert(0, '/Volumes/工作/赚钱/zeroeye/tools')

from health_check import retry_operation, check_http_service, check_tcp_port


class TestRetryOperation(unittest.TestCase):
    """Test the retry_operation function."""

    def test_retry_on_critical_status(self):
        """Test that retry_operation retries on CRITICAL status."""
        mock_func = MagicMock(side_effect=[
            ("CRITICAL", "Connection refused", 0),
            ("CRITICAL", "Connection refused", 0),
            ("OK", "Connected", 1.0)
        ])
        
        result = retry_operation(mock_func, retries=2, backoff_secs=0.01)
        
        self.assertEqual(result[0], "OK")
        self.assertEqual(mock_func.call_count, 3)

    def test_no_retry_on_warning_status(self):
        """Test that retry_operation does not retry on WARNING status."""
        mock_func = MagicMock(return_value=("WARNING", "HTTP 404", 404))
        
        result = retry_operation(mock_func, retries=2, backoff_secs=0.01)
        
        self.assertEqual(result[0], "WARNING")
        self.assertEqual(mock_func.call_count, 1)

    def test_no_retry_on_ok_status(self):
        """Test that retry_operation does not retry on OK status."""
        mock_func = MagicMock(return_value=("OK", "HTTP 200", 200))
        
        result = retry_operation(mock_func, retries=2, backoff_secs=0.01)
        
        self.assertEqual(result[0], "OK")
        self.assertEqual(mock_func.call_count, 1)

    def test_retry_on_timeout_error(self):
        """Test that retry_operation retries on timeout errors."""
        mock_func = MagicMock(side_effect=[
            ("CRITICAL", "Connection timeout (5s)", 0),
            ("OK", "Connected", 1.0)
        ])
        
        result = retry_operation(mock_func, retries=1, backoff_secs=0.01)
        
        self.assertEqual(result[0], "OK")
        self.assertEqual(mock_func.call_count, 2)

    def test_retry_on_http_5xx(self):
        """Test that retry_operation retries on 5xx HTTP errors."""
        mock_func = MagicMock(side_effect=[
            ("CRITICAL", "HTTP 503: Service Unavailable", 503),
            ("OK", "HTTP 200", 200)
        ])
        
        result = retry_operation(mock_func, retries=1, backoff_secs=0.01)
        
        self.assertEqual(result[0], "OK")
        self.assertEqual(mock_func.call_count, 2)

    def test_no_retry_on_http_4xx(self):
        """Test that retry_operation does not retry on 4xx HTTP errors."""
        mock_func = MagicMock(return_value=("WARNING", "HTTP 404: Not Found", 404))
        
        result = retry_operation(mock_func, retries=2, backoff_secs=0.01)
        
        self.assertEqual(result[0], "WARNING")
        self.assertEqual(mock_func.call_count, 1)


class TestHealthCheckIntegration(unittest.TestCase):
    """Integration tests for health check functions."""

    def test_check_http_service_returns_tuple(self):
        """Test that check_http_service returns a tuple."""
        # This will fail to connect, but should return a tuple
        result = check_http_service("localhost", 99999, "/health", 1)
        
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "CRITICAL")  # Should fail to connect

    def test_check_tcp_port_returns_tuple(self):
        """Test that check_tcp_port returns a tuple."""
        # This will fail to connect, but should return a tuple
        result = check_tcp_port("localhost", 99999, 1)
        
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "CRITICAL")  # Should fail to connect


if __name__ == '__main__':
    unittest.main()

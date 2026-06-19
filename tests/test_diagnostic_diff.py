import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.diagnostic_diff import load_json, diff_metadata, diff_modules

def test_diff_metadata():
    old = {"commit": "123", "passed": 1, "failed": 0, "only_old": True}
    new = {"commit": "456", "passed": 1, "failed": 0, "only_new": True}
    
    diff = diff_metadata(old, new)
    assert "only_new" in diff["added"]
    assert "only_old" in diff["removed"]
    assert diff["changed"]["commit"]["old"] == "123"
    assert diff["changed"]["commit"]["new"] == "456"
    assert "passed" not in diff["changed"]

def test_empty_input():
    # Test diffing two empty objects
    old = {}
    new = {}
    diff = diff_metadata(old, new)
    assert not diff["added"]
    assert not diff["removed"]
    assert not diff["changed"]
    
    mod_diff = diff_modules([], [])
    assert not mod_diff["status_changes"]
    assert not mod_diff["time_changes"]
    assert not mod_diff["regressions"]

def test_diff_modules_status_change():
    old = [{"name": "mod1", "status": "FAIL", "elapsed_seconds": 10}, 
           {"name": "mod2", "status": "PASS", "elapsed_seconds": 5}]
    new = [{"name": "mod1", "status": "PASS", "elapsed_seconds": 8},
           {"name": "mod2", "status": "FAIL", "elapsed_seconds": 6}]
           
    mod_diff = diff_modules(old, new)
    assert mod_diff["status_changes"]["mod1"]["old"] == "FAIL"
    assert mod_diff["status_changes"]["mod1"]["new"] == "PASS"
    assert mod_diff["status_changes"]["mod2"]["old"] == "PASS"
    assert mod_diff["status_changes"]["mod2"]["new"] == "FAIL"
    
    assert mod_diff["time_changes"]["mod1"]["diff"] == -2
    assert mod_diff["time_changes"]["mod2"]["diff"] == 1
    
    # Check that a regression (PASS -> FAIL) was detected
    assert mod_diff["regressions"] is True

def test_diff_modules_no_regression():
    old = [{"name": "mod1", "status": "FAIL"}]
    new = [{"name": "mod1", "status": "PASS"}]
    
    mod_diff = diff_modules(old, new)
    assert mod_diff["regressions"] is False

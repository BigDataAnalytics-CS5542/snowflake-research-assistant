"""
===================
Smoke test for the Snowflake Research Assistant backend.

Tests only endpoints that do NOT require a live Snowflake connection,
so this can run immediately after starting the backend without MFA.

Usage:
    pytest tests/smoke_test.py -v

Requires:
    Backend must be running on port 3001 before running this test.
    Start it with: uvicorn backend.app:app --port 3001
"""

import pytest
import requests

BASE_URL = "http://localhost:3001"


def test_health_endpoint():
    """Backend is running and healthy."""
    res = requests.get(f"{BASE_URL}/health")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data == {"status": "ok"}, f"Unexpected response: {data}"


def test_root_endpoint():
    """Root endpoint returns a welcome message."""
    res = requests.get(f"{BASE_URL}/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "message" in data, f"No 'message' key in response: {data}"


def test_history_endpoint_returns_list():
    """History endpoint returns a list (empty or populated)."""
    res = requests.get(f"{BASE_URL}/history")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert isinstance(data, list), f"Expected list, got {type(data)}"


def test_history_entry_structure():
    """If history has entries, each entry has the expected keys."""
    res = requests.get(f"{BASE_URL}/history")
    data = res.json()
    if len(data) == 0:
        pytest.skip("No history entries yet — skipping structure check.")
    entry = data[0]
    for key in ["timestamp", "query", "answer", "chunks"]:
        assert key in entry, f"Missing key '{key}' in history entry: {entry}"
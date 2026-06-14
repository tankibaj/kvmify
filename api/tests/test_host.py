"""Tests for the /host/stats router and host_service.

All psutil calls are monkeypatched — no real host metrics needed.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GB = 1024 ** 3


def _make_disk_usage(percent: float, used_gb: float = 100.0, total_gb: float = 200.0) -> MagicMock:
    du = MagicMock()
    du.percent = percent
    du.used = int(used_gb * _GB)
    du.total = int(total_gb * _GB)
    return du


def _make_virtual_memory(percent: float, used_gb: float = 8.0, total_gb: float = 16.0) -> MagicMock:
    vm = MagicMock()
    vm.percent = percent
    vm.used = int(used_gb * _GB)
    vm.total = int(total_gb * _GB)
    return vm


# ---------------------------------------------------------------------------
# 1. GET /host/stats — happy path
# ---------------------------------------------------------------------------

def test_get_host_stats_returns_correct_shape(client: TestClient, monkeypatch):
    """GET /host/stats returns HostStats with all expected fields."""
    monkeypatch.setattr("psutil.cpu_percent", lambda interval=None: 42.567)
    monkeypatch.setattr("psutil.virtual_memory", lambda: _make_virtual_memory(65.432))
    monkeypatch.setattr(
        "psutil.disk_usage",
        lambda path: _make_disk_usage(55.0) if path == "/" else _make_disk_usage(78.9),
    )
    monkeypatch.setattr("os.path.exists", lambda path: True)

    resp = client.get("/host/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "cpu_percent" in data
    assert "ram_percent" in data
    assert "disk_percent" in data
    assert "pool_percent" in data
    # Absolute GB + CPU-count fields (consumed by the sidebar + dashboard).
    for key in ("ram_used_gb", "ram_total_gb", "disk_used_gb", "disk_total_gb", "host_cpu_count"):
        assert key in data


def test_get_host_stats_returns_absolute_gb_and_cpu_count(client: TestClient, monkeypatch):
    """GET /host/stats reports RAM/disk used+total in GB and the logical CPU count."""
    monkeypatch.setattr("psutil.cpu_percent", lambda interval=None: 5.0)
    monkeypatch.setattr(
        "psutil.virtual_memory", lambda: _make_virtual_memory(50.0, used_gb=8.0, total_gb=16.0)
    )
    monkeypatch.setattr(
        "psutil.disk_usage",
        lambda path: _make_disk_usage(40.0, used_gb=120.0, total_gb=300.0),
    )
    monkeypatch.setattr("psutil.cpu_count", lambda logical=True: 12)
    monkeypatch.setattr("os.path.exists", lambda path: True)

    data = client.get("/host/stats").json()
    assert data["ram_used_gb"] == 8.0
    assert data["ram_total_gb"] == 16.0
    assert data["disk_used_gb"] == 120.0
    assert data["disk_total_gb"] == 300.0
    assert data["host_cpu_count"] == 12


def test_get_host_stats_rounds_to_one_decimal(client: TestClient, monkeypatch):
    """GET /host/stats rounds all values to 1 decimal place."""
    monkeypatch.setattr("psutil.cpu_percent", lambda interval=None: 33.3333)
    monkeypatch.setattr("psutil.virtual_memory", lambda: _make_virtual_memory(66.6666))
    monkeypatch.setattr(
        "psutil.disk_usage",
        lambda path: _make_disk_usage(50.55),
    )
    monkeypatch.setattr("os.path.exists", lambda path: True)

    resp = client.get("/host/stats")
    assert resp.status_code == 200
    data = resp.json()
    # All should be at most 1 decimal
    assert data["cpu_percent"] == round(33.3333, 1)
    assert data["ram_percent"] == round(66.6666, 1)
    assert data["disk_percent"] == round(50.55, 1)


def test_get_host_stats_values_are_correct(client: TestClient, monkeypatch):
    """GET /host/stats returns the exact values from psutil."""
    monkeypatch.setattr("psutil.cpu_percent", lambda interval=None: 10.0)
    monkeypatch.setattr("psutil.virtual_memory", lambda: _make_virtual_memory(20.0))

    def _disk(path: str) -> MagicMock:
        if path == "/":
            return _make_disk_usage(30.0)
        return _make_disk_usage(40.0)

    monkeypatch.setattr("psutil.disk_usage", _disk)
    monkeypatch.setattr("os.path.exists", lambda path: True)

    resp = client.get("/host/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cpu_percent"] == 10.0
    assert data["ram_percent"] == 20.0
    assert data["disk_percent"] == 30.0
    assert data["pool_percent"] == 40.0


# ---------------------------------------------------------------------------
# 2. GET /host/stats — pool path missing
# ---------------------------------------------------------------------------

def test_get_host_stats_pool_path_missing_returns_none(client: TestClient, monkeypatch):
    """GET /host/stats returns pool_percent=None when pool path doesn't exist."""
    monkeypatch.setattr("psutil.cpu_percent", lambda interval=None: 10.0)
    monkeypatch.setattr("psutil.virtual_memory", lambda: _make_virtual_memory(20.0))
    monkeypatch.setattr("psutil.disk_usage", lambda path: _make_disk_usage(30.0))
    # Simulate missing pool path
    monkeypatch.setattr("os.path.exists", lambda path: False)

    resp = client.get("/host/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pool_percent"] is None


def test_get_host_stats_pool_path_missing_does_not_crash(client: TestClient, monkeypatch):
    """GET /host/stats still returns 200 even if pool path is missing."""
    monkeypatch.setattr("psutil.cpu_percent", lambda interval=None: 5.0)
    monkeypatch.setattr("psutil.virtual_memory", lambda: _make_virtual_memory(50.0))
    monkeypatch.setattr("psutil.disk_usage", lambda path: _make_disk_usage(25.0))
    monkeypatch.setattr("os.path.exists", lambda path: False)

    resp = client.get("/host/stats")
    assert resp.status_code == 200
    assert "cpu_percent" in resp.json()

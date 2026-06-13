"""Tests for GET /vms/{name}/stats and sample_cpu_percent.

All libvirt calls and time.sleep are mocked — no real hypervisor needed.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import libvirt
import pytest
from fastapi.testclient import TestClient

from api.services import vm_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_domain(
    name: str = "test-vm",
    state: int = libvirt.VIR_DOMAIN_RUNNING,
    vcpus: int = 2,
    max_mem_kb: int = 4 * 1024 * 1024,   # 4 GiB
    mem_kb: int = 2 * 1024 * 1024,        # 2 GiB
    cpu_time1: int = 1_000_000_000,        # 1 s in ns
    cpu_time2: int = 2_000_000_000,        # 2 s in ns
) -> MagicMock:
    """Return a mock virDomain with three sequential domain.info() calls.

    The router calls sample_cpu_percent (which consumes 2 info() calls) and
    then calls domain.info() once more for RAM stats — 3 total.
    """
    domain = MagicMock(name=f"virDomain:{name}")
    domain.name.return_value = name
    domain.state.return_value = (state, 0)
    # info() returns (state, maxMem_kb, mem_kb, vcpus, cpuTime_ns)
    domain.info.side_effect = [
        (state, max_mem_kb, mem_kb, vcpus, cpu_time1),  # sample 1 (cpu)
        (state, max_mem_kb, mem_kb, vcpus, cpu_time2),  # sample 2 (cpu)
        (state, max_mem_kb, mem_kb, vcpus, cpu_time2),  # router RAM read
    ]
    return domain


# ---------------------------------------------------------------------------
# 1. GET /vms/{name}/stats — shape
# ---------------------------------------------------------------------------

def test_vm_stats_returns_vmstats_shape(client: TestClient, patch_libvirt, mock_conn):
    """GET /vms/{name}/stats returns VMStats with expected fields."""
    domain = _make_mock_domain("running-vm")
    mock_conn.lookupByName.return_value = domain
    mock_conn.getInfo.return_value = [None, None, 4]  # 4 host CPUs at index 2

    with patch("api.services.vm_service._sleep"):
        resp = client.get("/vms/running-vm/stats")

    assert resp.status_code == 200
    data = resp.json()
    assert "cpu_percent" in data
    assert "ram_percent" in data
    assert "ram_used_mb" in data


def test_vm_stats_cpu_percent_computed_correctly(client: TestClient, patch_libvirt, mock_conn):
    """GET /vms/{name}/stats computes cpu_percent from two domain.info() samples."""
    # cpu_time delta = 2_000_000_000 - 1_000_000_000 = 1_000_000_000 ns = 1 s
    # interval = 0.5 s, host_cpus = 4
    # cpu_pct = 1_000_000_000 / (0.5 * 1e9 * 4) * 100 = 1e9 / 2e9 * 100 = 50.0
    domain = _make_mock_domain(
        "running-vm",
        cpu_time1=1_000_000_000,
        cpu_time2=2_000_000_000,
        max_mem_kb=4 * 1024 * 1024,
        mem_kb=2 * 1024 * 1024,
    )
    mock_conn.lookupByName.return_value = domain
    mock_conn.getInfo.return_value = [None, None, 4]

    with patch("api.services.vm_service._sleep"):
        resp = client.get("/vms/running-vm/stats")

    assert resp.status_code == 200
    data = resp.json()
    assert data["cpu_percent"] == 50.0


def test_vm_stats_ram_percent_computed_correctly(client: TestClient, patch_libvirt, mock_conn):
    """GET /vms/{name}/stats computes ram_percent = mem/maxMem*100."""
    # max_mem=4096 KiB, mem=2048 KiB → 50.0%
    domain = _make_mock_domain(
        "running-vm",
        max_mem_kb=4096,
        mem_kb=2048,
    )
    mock_conn.lookupByName.return_value = domain
    mock_conn.getInfo.return_value = [None, None, 2]

    with patch("api.services.vm_service._sleep"):
        resp = client.get("/vms/running-vm/stats")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ram_percent"] == 50.0
    assert data["ram_used_mb"] == 2  # 2048 KiB // 1024 = 2 MiB


def test_vm_stats_ram_used_mb_correct(client: TestClient, patch_libvirt, mock_conn):
    """GET /vms/{name}/stats returns ram_used_mb = mem_kb // 1024."""
    domain = _make_mock_domain("running-vm", max_mem_kb=8192, mem_kb=3072)
    mock_conn.lookupByName.return_value = domain
    mock_conn.getInfo.return_value = [None, None, 2]

    with patch("api.services.vm_service._sleep"):
        resp = client.get("/vms/running-vm/stats")

    assert resp.status_code == 200
    assert resp.json()["ram_used_mb"] == 3  # 3072 // 1024


def test_vm_stats_sleep_not_called_when_monkeypatched(
    client: TestClient, patch_libvirt, mock_conn
):
    """_sleep is monkeypatched — real time.sleep is never invoked."""
    domain = _make_mock_domain("running-vm")
    mock_conn.lookupByName.return_value = domain
    mock_conn.getInfo.return_value = [None, None, 2]

    sleep_mock = MagicMock()
    with patch("api.services.vm_service._sleep", sleep_mock):
        resp = client.get("/vms/running-vm/stats")

    assert resp.status_code == 200
    # _sleep was called with the interval
    sleep_mock.assert_called_once_with(0.5)


# ---------------------------------------------------------------------------
# 2. GET /vms/{name}/stats — 404 for missing domain
# ---------------------------------------------------------------------------

def test_vm_stats_not_found_returns_404(client: TestClient, patch_libvirt, mock_conn):
    """GET /vms/{name}/stats returns 404 when domain doesn't exist."""
    mock_conn.lookupByName.side_effect = libvirt.libvirtError("Domain not found")
    resp = client.get("/vms/ghost/stats")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 3. sample_cpu_percent unit tests
# ---------------------------------------------------------------------------

def test_sample_cpu_percent_returns_float():
    """sample_cpu_percent returns a float between 0 and 100."""
    conn = MagicMock()
    conn.getInfo.return_value = [None, None, 2]
    domain = MagicMock()
    domain.info.side_effect = [
        (1, 4096, 2048, 2, 500_000_000),
        (1, 4096, 2048, 2, 600_000_000),
    ]
    conn.lookupByName.return_value = domain

    with patch("api.services.vm_service._sleep"):
        result = vm_service.sample_cpu_percent(conn, "vm", interval=0.5)

    assert result is not None
    assert 0.0 <= result <= 100.0


def test_sample_cpu_percent_clamps_to_100():
    """sample_cpu_percent clamps values above 100 to 100."""
    conn = MagicMock()
    conn.getInfo.return_value = [None, None, 1]
    domain = MagicMock()
    # Huge delta to force > 100
    domain.info.side_effect = [
        (1, 4096, 2048, 2, 0),
        (1, 4096, 2048, 2, 10_000_000_000_000),
    ]
    conn.lookupByName.return_value = domain

    with patch("api.services.vm_service._sleep"):
        result = vm_service.sample_cpu_percent(conn, "vm", interval=0.5)

    assert result == 100.0


def test_sample_cpu_percent_returns_none_on_error():
    """sample_cpu_percent returns None when domain.info() raises."""
    conn = MagicMock()
    conn.getInfo.return_value = [None, None, 2]
    domain = MagicMock()
    domain.info.side_effect = libvirt.libvirtError("domain gone")
    conn.lookupByName.return_value = domain

    with patch("api.services.vm_service._sleep"):
        result = vm_service.sample_cpu_percent(conn, "vm")

    assert result is None

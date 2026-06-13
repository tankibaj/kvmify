"""Tests for the /vms/{name}/snapshots router and snapshot_service.

All libvirt calls are mocked — no real hypervisor needed.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import libvirt
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_snap_xml(
    name: str = "snap1",
    creation_time: str = "1700000000",
    description: str = "test snap",
    state: str = "shutoff",
) -> str:
    return (
        f"<domainsnapshot>"
        f"<name>{name}</name>"
        f"<creationTime>{creation_time}</creationTime>"
        f"<description>{description}</description>"
        f"<state>{state}</state>"
        f"</domainsnapshot>"
    )


def _make_mock_snap(
    name: str = "snap1",
    is_current: bool = False,
    creation_time: str = "1700000000",
    description: str = "test snap",
    state: str = "shutoff",
) -> MagicMock:
    snap = MagicMock(name=f"virDomainSnapshot:{name}")
    snap.getXMLDesc.return_value = _make_snap_xml(name, creation_time, description, state)
    snap.isCurrent.return_value = is_current
    snap.delete = MagicMock(return_value=0)
    return snap


def _make_mock_domain_with_snaps(
    vm_name: str = "test-vm",
    snaps: list | None = None,
) -> MagicMock:
    domain = MagicMock(name=f"virDomain:{vm_name}")
    domain.name.return_value = vm_name
    domain.listAllSnapshots.return_value = snaps or []
    # snapshotLookupByName: raise by default (not found)
    domain.snapshotLookupByName.side_effect = libvirt.libvirtError("not found")
    domain.snapshotCreateXML = MagicMock()
    domain.revertToSnapshot = MagicMock(return_value=0)
    return domain


# ---------------------------------------------------------------------------
# 1. GET /{name}/snapshots — list shape
# ---------------------------------------------------------------------------

def test_list_snapshots_returns_list(client: TestClient, patch_libvirt, mock_conn):
    """GET /vms/{name}/snapshots returns list with correct fields."""
    snap1 = _make_mock_snap("snap1", is_current=True)
    snap2 = _make_mock_snap("snap2", is_current=False)
    domain = _make_mock_domain_with_snaps("my-vm", snaps=[snap1, snap2])
    mock_conn.lookupByName.return_value = domain

    resp = client.get("/vms/my-vm/snapshots")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    names = {s["name"] for s in data}
    assert names == {"snap1", "snap2"}
    # Check required fields
    for item in data:
        assert "name" in item
        assert "is_current" in item
    # is_current should be set on snap1
    current_snaps = [s for s in data if s["is_current"]]
    assert len(current_snaps) == 1
    assert current_snaps[0]["name"] == "snap1"


def test_list_snapshots_empty(client: TestClient, patch_libvirt, mock_conn):
    """GET /vms/{name}/snapshots returns empty list when no snapshots."""
    domain = _make_mock_domain_with_snaps("my-vm", snaps=[])
    mock_conn.lookupByName.return_value = domain

    resp = client.get("/vms/my-vm/snapshots")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_snapshots_parses_fields(client: TestClient, patch_libvirt, mock_conn):
    """GET /vms/{name}/snapshots correctly parses name, created, description, state."""
    snap = _make_mock_snap(
        name="mysnap",
        creation_time="1700000000",
        description="A test snapshot",
        state="running",
    )
    domain = _make_mock_domain_with_snaps("my-vm", snaps=[snap])
    mock_conn.lookupByName.return_value = domain

    resp = client.get("/vms/my-vm/snapshots")
    assert resp.status_code == 200
    data = resp.json()
    item = data[0]
    assert item["name"] == "mysnap"
    assert item["description"] == "A test snapshot"
    assert item["state"] == "running"
    assert item["created"] is not None
    assert "2023" in item["created"]  # unix 1700000000 → 2023-11-14…


def test_list_snapshots_missing_vm_returns_404(client: TestClient, patch_libvirt, mock_conn):
    """GET /vms/{name}/snapshots returns 404 when domain doesn't exist."""
    mock_conn.lookupByName.side_effect = libvirt.libvirtError("Domain not found")
    resp = client.get("/vms/ghost/snapshots")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 2. POST /{name}/snapshots — take snapshot
# ---------------------------------------------------------------------------

def test_take_snapshot_calls_snapshotCreateXML(client: TestClient, patch_libvirt, mock_conn):
    """POST /vms/{name}/snapshots calls snapshotCreateXML and returns SnapshotInfo."""
    new_snap = _make_mock_snap("snap-new", is_current=True)
    domain = _make_mock_domain_with_snaps("my-vm")
    domain.snapshotCreateXML.return_value = new_snap
    mock_conn.lookupByName.return_value = domain

    resp = client.post("/vms/my-vm/snapshots", json={"name": "snap-new", "description": "fresh"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "snap-new"
    assert data["is_current"] is True
    domain.snapshotCreateXML.assert_called_once()
    # XML should contain the name
    call_xml = domain.snapshotCreateXML.call_args[0][0]
    assert "snap-new" in call_xml
    assert "fresh" in call_xml


def test_take_snapshot_without_description(client: TestClient, patch_libvirt, mock_conn):
    """POST /vms/{name}/snapshots without description omits description from XML."""
    new_snap = _make_mock_snap("nodesc")
    domain = _make_mock_domain_with_snaps("my-vm")
    domain.snapshotCreateXML.return_value = new_snap
    mock_conn.lookupByName.return_value = domain

    resp = client.post("/vms/my-vm/snapshots", json={"name": "nodesc"})
    assert resp.status_code == 201
    call_xml = domain.snapshotCreateXML.call_args[0][0]
    assert "<description>" not in call_xml


def test_take_snapshot_duplicate_name_returns_409(client: TestClient, patch_libvirt, mock_conn):
    """POST /vms/{name}/snapshots with existing snap name returns 409."""
    existing_snap = _make_mock_snap("dup")
    domain = _make_mock_domain_with_snaps("my-vm")
    # snapshotLookupByName succeeds → name exists
    domain.snapshotLookupByName.side_effect = None
    domain.snapshotLookupByName.return_value = existing_snap
    mock_conn.lookupByName.return_value = domain

    resp = client.post("/vms/my-vm/snapshots", json={"name": "dup"})
    assert resp.status_code == 409


def test_take_snapshot_missing_vm_returns_404(client: TestClient, patch_libvirt, mock_conn):
    """POST /vms/{name}/snapshots returns 404 when domain doesn't exist."""
    mock_conn.lookupByName.side_effect = libvirt.libvirtError("Domain not found")
    resp = client.post("/vms/ghost/snapshots", json={"name": "snap"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 3. POST /{name}/snapshots/{snap}/restore
# ---------------------------------------------------------------------------

def test_restore_snapshot_calls_revertToSnapshot(client: TestClient, patch_libvirt, mock_conn):
    """POST /vms/{name}/snapshots/{snap}/restore calls domain.revertToSnapshot."""
    snap = _make_mock_snap("snap1")
    domain = _make_mock_domain_with_snaps("my-vm")
    domain.snapshotLookupByName.side_effect = None
    domain.snapshotLookupByName.return_value = snap
    mock_conn.lookupByName.return_value = domain

    resp = client.post("/vms/my-vm/snapshots/snap1/restore")
    assert resp.status_code == 200
    domain.revertToSnapshot.assert_called_once_with(snap, 0)
    data = resp.json()
    assert "snap1" in data["message"]


def test_restore_snapshot_missing_snap_returns_404(client: TestClient, patch_libvirt, mock_conn):
    """POST /vms/{name}/snapshots/{snap}/restore returns 404 for missing snapshot."""
    domain = _make_mock_domain_with_snaps("my-vm")
    # snapshotLookupByName raises → snapshot not found
    domain.snapshotLookupByName.side_effect = libvirt.libvirtError("not found")
    mock_conn.lookupByName.return_value = domain

    resp = client.post("/vms/my-vm/snapshots/ghost-snap/restore")
    assert resp.status_code == 404


def test_restore_snapshot_missing_vm_returns_404(client: TestClient, patch_libvirt, mock_conn):
    """POST /vms/{name}/snapshots/{snap}/restore returns 404 for missing VM."""
    mock_conn.lookupByName.side_effect = libvirt.libvirtError("Domain not found")
    resp = client.post("/vms/ghost/snapshots/snap1/restore")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 4. DELETE /{name}/snapshots/{snap}
# ---------------------------------------------------------------------------

def test_delete_snapshot_calls_snap_delete(client: TestClient, patch_libvirt, mock_conn):
    """DELETE /vms/{name}/snapshots/{snap} calls snap.delete(0)."""
    snap = _make_mock_snap("snap1")
    domain = _make_mock_domain_with_snaps("my-vm")
    domain.snapshotLookupByName.side_effect = None
    domain.snapshotLookupByName.return_value = snap
    mock_conn.lookupByName.return_value = domain

    resp = client.delete("/vms/my-vm/snapshots/snap1")
    assert resp.status_code == 204
    snap.delete.assert_called_once_with(0)


def test_delete_snapshot_missing_snap_returns_404(client: TestClient, patch_libvirt, mock_conn):
    """DELETE /vms/{name}/snapshots/{snap} returns 404 for missing snapshot."""
    domain = _make_mock_domain_with_snaps("my-vm")
    domain.snapshotLookupByName.side_effect = libvirt.libvirtError("not found")
    mock_conn.lookupByName.return_value = domain

    resp = client.delete("/vms/my-vm/snapshots/ghost-snap")
    assert resp.status_code == 404


def test_delete_snapshot_missing_vm_returns_404(client: TestClient, patch_libvirt, mock_conn):
    """DELETE /vms/{name}/snapshots/{snap} returns 404 for missing VM."""
    mock_conn.lookupByName.side_effect = libvirt.libvirtError("Domain not found")
    resp = client.delete("/vms/ghost/snapshots/snap1")
    assert resp.status_code == 404

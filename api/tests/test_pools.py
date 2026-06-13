"""Tests for the /pools router and pool_service."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, call

import libvirt
import pytest
from fastapi.testclient import TestClient

from api.services import settings_service


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------

POOL_XML = """
<pool type='dir'>
  <name>default</name>
  <target>
    <path>/mnt/nvme1/kvm/pool</path>
  </target>
</pool>
"""

POOL_XML_SECONDARY = """
<pool type='dir'>
  <name>data</name>
  <target>
    <path>/mnt/data/vms</path>
  </target>
</pool>
"""


def _make_pool(name: str, xml: str, *, active: bool = True, autostart: bool = True, vol_count: int = 0) -> MagicMock:
    pool = MagicMock(name=f"virStoragePool:{name}")
    pool.name.return_value = name
    pool.XMLDesc.return_value = xml
    pool.isActive.return_value = active
    pool.autostart.return_value = autostart
    pool.numOfVolumes.return_value = vol_count
    pool.listAllVolumes.return_value = [MagicMock() for _ in range(vol_count)]
    # info() → [state_int, capacity, allocation, available]
    pool.info.return_value = [1 if active else 0, 500 * 1024**3, 10 * 1024**3, 490 * 1024**3]
    pool.create = MagicMock(return_value=0)
    pool.destroy = MagicMock(return_value=0)
    pool.undefine = MagicMock(return_value=0)
    pool.build = MagicMock(return_value=0)
    pool.refresh = MagicMock(return_value=0)
    pool.setAutostart = MagicMock(return_value=0)
    return pool


# ---------------------------------------------------------------------------
# GET /pools
# ---------------------------------------------------------------------------

def test_list_pools_returns_list(client: TestClient, patch_libvirt, mock_conn, tmp_settings):
    """GET /pools returns a list with the correct shape."""
    pool = _make_pool("default", POOL_XML)
    mock_conn.listAllStoragePools.return_value = [pool]

    resp = client.get("/pools")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    item = data[0]
    assert item["name"] == "default"
    assert item["state"] == "active"
    assert item["type"] == "dir"
    assert item["path"] == "/mnt/nvme1/kvm/pool"
    assert "capacity" in item
    assert "available" in item
    assert "volume_count" in item


def test_list_pools_is_default_flag(client: TestClient, patch_libvirt, mock_conn, tmp_settings):
    """The pool matching the stored default gets is_default=True."""
    # Seed default_pool to "default" via tmp settings
    settings_service.set_default_pool("default")

    pool_default = _make_pool("default", POOL_XML)
    pool_data = _make_pool("data", POOL_XML_SECONDARY)
    mock_conn.listAllStoragePools.return_value = [pool_default, pool_data]

    resp = client.get("/pools")
    data = resp.json()
    by_name = {p["name"]: p for p in data}
    assert by_name["default"]["is_default"] is True
    assert by_name["data"]["is_default"] is False


# ---------------------------------------------------------------------------
# POST /pools
# ---------------------------------------------------------------------------

def test_create_pool_calls_define_xml(client: TestClient, patch_libvirt, mock_conn, tmp_settings):
    """POST /pools calls storagePoolDefineXML and returns 201."""
    # Pool doesn't exist yet — lookup raises
    import libvirt as lv
    mock_conn.storagePoolLookupByName.side_effect = lv.libvirtError("not found")

    new_pool = _make_pool("data", POOL_XML_SECONDARY)
    mock_conn.storagePoolDefineXML.return_value = new_pool

    resp = client.post("/pools", json={"name": "data", "path": "/mnt/data/vms"})
    assert resp.status_code == 201
    mock_conn.storagePoolDefineXML.assert_called_once()
    xml_arg = mock_conn.storagePoolDefineXML.call_args[0][0]
    assert "data" in xml_arg
    assert "/mnt/data/vms" in xml_arg
    new_pool.build.assert_called_once_with(0)
    new_pool.create.assert_called_once_with(0)
    new_pool.setAutostart.assert_called_once_with(True)


def test_create_pool_duplicate_returns_400(client: TestClient, patch_libvirt, mock_conn, tmp_settings):
    """POST /pools with duplicate name returns 400."""
    existing = _make_pool("default", POOL_XML)
    # Lookup succeeds → pool exists
    mock_conn.storagePoolLookupByName.side_effect = None
    mock_conn.storagePoolLookupByName.return_value = existing

    resp = client.post("/pools", json={"name": "default", "path": "/some/path"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /pools/{name}
# ---------------------------------------------------------------------------

def test_delete_default_pool_returns_409(client: TestClient, patch_libvirt, mock_conn, tmp_settings):
    """DELETE /pools/default returns 409 when it is the current default."""
    settings_service.set_default_pool("default")

    pool = _make_pool("default", POOL_XML, vol_count=0)
    mock_conn.storagePoolLookupByName.side_effect = None
    mock_conn.storagePoolLookupByName.return_value = pool

    resp = client.delete("/pools/default")
    assert resp.status_code == 409


def test_delete_pool_with_volumes_returns_409(client: TestClient, patch_libvirt, mock_conn, tmp_settings):
    """DELETE /pools/data without force=true returns 409 when volumes exist."""
    settings_service.set_default_pool("default")

    pool = _make_pool("data", POOL_XML_SECONDARY, vol_count=3)
    mock_conn.storagePoolLookupByName.side_effect = None
    mock_conn.storagePoolLookupByName.return_value = pool

    resp = client.delete("/pools/data")
    assert resp.status_code == 409


def test_delete_pool_with_volumes_force_succeeds(client: TestClient, patch_libvirt, mock_conn, tmp_settings):
    """DELETE /pools/data?force=true deletes even when volumes exist."""
    settings_service.set_default_pool("default")

    pool = _make_pool("data", POOL_XML_SECONDARY, vol_count=3)
    mock_conn.storagePoolLookupByName.side_effect = None
    mock_conn.storagePoolLookupByName.return_value = pool

    resp = client.delete("/pools/data?force=true")
    assert resp.status_code == 204
    pool.destroy.assert_called_once()
    pool.undefine.assert_called_once()


def test_delete_pool_not_found_returns_404(client: TestClient, patch_libvirt, mock_conn, tmp_settings):
    """DELETE /pools/ghost returns 404 when pool doesn't exist."""
    settings_service.set_default_pool("default")
    import libvirt as lv
    mock_conn.storagePoolLookupByName.side_effect = lv.libvirtError("not found")

    resp = client.delete("/pools/ghost")
    assert resp.status_code == 404


def test_delete_empty_non_default_pool_succeeds(client: TestClient, patch_libvirt, mock_conn, tmp_settings):
    """DELETE /pools/data (empty, non-default) returns 204."""
    settings_service.set_default_pool("default")

    pool = _make_pool("data", POOL_XML_SECONDARY, vol_count=0)
    mock_conn.storagePoolLookupByName.side_effect = None
    mock_conn.storagePoolLookupByName.return_value = pool

    resp = client.delete("/pools/data")
    assert resp.status_code == 204
    pool.destroy.assert_called_once()
    pool.undefine.assert_called_once()


# ---------------------------------------------------------------------------
# PATCH /pools/{name}
# ---------------------------------------------------------------------------

def test_patch_pool_start(client: TestClient, patch_libvirt, mock_conn, tmp_settings):
    """PATCH /pools/{name} with action=start calls pool.create(0)."""
    pool = _make_pool("data", POOL_XML_SECONDARY, active=False)
    mock_conn.storagePoolLookupByName.side_effect = None
    mock_conn.storagePoolLookupByName.return_value = pool

    resp = client.patch("/pools/data", json={"action": "start"})
    assert resp.status_code == 200
    pool.create.assert_called_once_with(0)


def test_patch_pool_stop(client: TestClient, patch_libvirt, mock_conn, tmp_settings):
    """PATCH /pools/{name} with action=stop calls pool.destroy()."""
    pool = _make_pool("data", POOL_XML_SECONDARY)
    mock_conn.storagePoolLookupByName.side_effect = None
    mock_conn.storagePoolLookupByName.return_value = pool

    resp = client.patch("/pools/data", json={"action": "stop"})
    assert resp.status_code == 200
    pool.destroy.assert_called_once()


def test_patch_pool_refresh(client: TestClient, patch_libvirt, mock_conn, tmp_settings):
    """PATCH /pools/{name} with action=refresh calls pool.refresh(0)."""
    pool = _make_pool("data", POOL_XML_SECONDARY)
    mock_conn.storagePoolLookupByName.side_effect = None
    mock_conn.storagePoolLookupByName.return_value = pool

    resp = client.patch("/pools/data", json={"action": "refresh"})
    assert resp.status_code == 200
    pool.refresh.assert_called_once_with(0)


def test_patch_pool_autostart(client: TestClient, patch_libvirt, mock_conn, tmp_settings):
    """PATCH /pools/{name} with autostart=false calls pool.setAutostart(0)."""
    pool = _make_pool("data", POOL_XML_SECONDARY)
    mock_conn.storagePoolLookupByName.side_effect = None
    mock_conn.storagePoolLookupByName.return_value = pool

    resp = client.patch("/pools/data", json={"autostart": False})
    assert resp.status_code == 200
    pool.setAutostart.assert_called_once_with(0)


# ---------------------------------------------------------------------------
# POST /pools/{name}/default
# ---------------------------------------------------------------------------

def test_set_default_pool(client: TestClient, patch_libvirt, mock_conn, tmp_settings):
    """POST /pools/{name}/default updates the settings file."""
    pool = _make_pool("data", POOL_XML_SECONDARY)
    mock_conn.storagePoolLookupByName.side_effect = None
    mock_conn.storagePoolLookupByName.return_value = pool

    resp = client.post("/pools/data/default")
    assert resp.status_code == 200
    assert resp.json() == {"default_pool": "data"}
    assert settings_service.get_default_pool() == "data"


def test_set_default_pool_not_found_returns_404(client: TestClient, patch_libvirt, mock_conn, tmp_settings):
    """POST /pools/ghost/default returns 404 when pool doesn't exist."""
    import libvirt as lv
    mock_conn.storagePoolLookupByName.side_effect = lv.libvirtError("not found")

    resp = client.post("/pools/ghost/default")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# settings_service unit tests (no HTTP)
# ---------------------------------------------------------------------------

def test_settings_service_default_when_file_missing(tmp_settings):
    """get_default_pool() returns 'default' when settings file is absent."""
    from api.services import settings_service
    assert settings_service.get_default_pool() == "default"


def test_settings_service_set_and_get(tmp_settings):
    """set_default_pool / get_default_pool round-trips correctly."""
    from api.services import settings_service
    settings_service.set_default_pool("my-pool")
    assert settings_service.get_default_pool() == "my-pool"


def test_settings_service_creates_file(tmp_settings):
    """set_default_pool creates the settings file if it doesn't exist."""
    from api.services import settings_service
    settings_service.set_default_pool("my-pool")
    assert tmp_settings.exists()
    data = json.loads(tmp_settings.read_text())
    assert data["default_pool"] == "my-pool"

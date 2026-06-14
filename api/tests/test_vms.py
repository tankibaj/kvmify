"""Tests for the /vms router and vm_service.

All libvirt and subprocess calls are mocked — no real hypervisor needed.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from typing import Generator
from unittest.mock import MagicMock, call, patch

import libvirt
import pytest
from fastapi.testclient import TestClient

from api import config
from api.services.cloudinit_service import mask_to_prefix


# ---------------------------------------------------------------------------
# Domain XML fixtures
# ---------------------------------------------------------------------------

def _make_domain_xml(
    name: str = "test-vm",
    vnc_port: int = 5900,
    network: str = "default",
    iface_type: str = "network",
) -> str:
    if iface_type == "direct":
        iface_xml = "<interface type='direct'><source dev='enp4s0' mode='bridge'/></interface>"
    else:
        iface_xml = f"<interface type='network'><source network='{network}'/></interface>"
    return f"""
<domain type='kvm'>
  <name>{name}</name>
  <devices>
    {iface_xml}
    <disk type='file' device='disk'>
      <source file='/mnt/nvme1/kvm/pool/vms/{name}.qcow2'/>
      <target dev='vda' bus='virtio'/>
    </disk>
    <disk type='file' device='cdrom'>
      <source file='/home/naim/kvmify/seeds/{name}-seed.iso'/>
      <target dev='sda' bus='sata'/>
    </disk>
    <graphics type='vnc' port='{vnc_port}' listen='127.0.0.1'/>
  </devices>
</domain>
"""


def _make_mock_domain(
    name: str = "test-vm",
    state: int = libvirt.VIR_DOMAIN_RUNNING,
    vcpus: int = 2,
    ram_mb: int = 2048,
    vnc_port: int = 5900,
    network: str = "default",
    iface_type: str = "network",
    ip: str | None = "192.168.1.100",
) -> MagicMock:
    domain = MagicMock(name=f"virDomain:{name}")
    domain.name.return_value = name
    domain.state.return_value = (state, 0)
    domain.maxVcpus.return_value = vcpus
    domain.maxMemory.return_value = ram_mb * 1024  # KB
    domain.XMLDesc.return_value = _make_domain_xml(name, vnc_port, network, iface_type)
    domain.create = MagicMock(return_value=0)
    domain.shutdown = MagicMock(return_value=0)
    domain.reboot = MagicMock(return_value=0)
    domain.destroy = MagicMock(return_value=0)
    domain.undefine = MagicMock(return_value=0)
    domain.undefineFlags = MagicMock(return_value=0)
    domain.setVcpusFlags = MagicMock(return_value=0)
    domain.setMemoryFlags = MagicMock(return_value=0)
    domain.blockResize = MagicMock(return_value=0)
    domain.detachDeviceFlags = MagicMock(return_value=0)
    domain.attachDeviceFlags = MagicMock(return_value=0)
    domain.getCPUStats = MagicMock(return_value=[{"cpu_time": 1000000}])
    domain.memoryStats = MagicMock(return_value={"actual": ram_mb * 1024, "unused": 512 * 1024, "rss": 1024 * 1024})

    # IP via interfaceAddresses
    if ip:
        domain.interfaceAddresses.return_value = {
            "enp1s0": {
                "addrs": [{"addr": ip, "prefix": 24, "type": libvirt.VIR_IP_ADDR_TYPE_IPV4}]
            }
        }
    else:
        domain.interfaceAddresses.return_value = {}

    return domain


# ---------------------------------------------------------------------------
# Helper: stub out os.path.exists for base image
# ---------------------------------------------------------------------------

BASE_IMG_EXISTS_PATCH = "api.services.vm_service.os.path.exists"
SUBPROCESS_PATCH = "api.services.vm_service.subprocess.run"
WRITE_SEED_PATCH = "api.services.cloudinit_service.write_seed_inputs"
TIME_PATCH = "api.services.vm_service.time"
SETTINGS_DEFAULT_POOL_PATCH = "api.services.vm_service.settings_service.get_default_pool"
POOL_PATH_PATCH = "api.services.vm_service.pool_service._pool_path_from_xml"


# ---------------------------------------------------------------------------
# 1. GET /vms — list shape
# ---------------------------------------------------------------------------

def test_list_vms_returns_list(client: TestClient, patch_libvirt, mock_conn):
    """GET /vms returns a list with expected shape."""
    d1 = _make_mock_domain("vm1", state=libvirt.VIR_DOMAIN_RUNNING)
    d2 = _make_mock_domain("vm2", state=libvirt.VIR_DOMAIN_SHUTOFF, ip=None)
    mock_conn.listAllDomains.return_value = [d1, d2]

    resp = client.get("/vms")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    names = {d["name"] for d in data}
    assert names == {"vm1", "vm2"}
    states = {d["name"]: d["state"] for d in data}
    assert states["vm1"] == "running"
    assert states["vm2"] == "shutoff"
    # Check all required fields present
    for item in data:
        assert "name" in item
        assert "state" in item
        assert "vcpus" in item
        assert "ram_mb" in item


def test_list_vms_includes_network(client: TestClient, patch_libvirt, mock_conn):
    """GET /vms includes network field extracted from XML."""
    d = _make_mock_domain("vm-net", network="public")
    mock_conn.listAllDomains.return_value = [d]

    resp = client.get("/vms")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["network"] == "public"


def test_list_vms_empty(client: TestClient, patch_libvirt, mock_conn):
    """GET /vms returns empty list when no domains exist."""
    mock_conn.listAllDomains.return_value = []
    resp = client.get("/vms")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# 2. GET /vms/{name} — detail shape
# ---------------------------------------------------------------------------

def test_get_vm_detail(client: TestClient, patch_libvirt, mock_conn):
    """GET /vms/{name} returns VMDetail with all expected fields."""
    d = _make_mock_domain("my-vm", vnc_port=5901, ram_mb=4096)
    mock_conn.lookupByName.return_value = d

    resp = client.get("/vms/my-vm")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "my-vm"
    assert data["vcpus"] == 2
    assert data["ram_mb"] == 4096
    assert data["vnc_port"] == 5901
    assert data["ip"] == "192.168.1.100"
    assert "ram_total_mb" in data


# ---------------------------------------------------------------------------
# 3. GET /vms/{name} — 404 for missing domain
# ---------------------------------------------------------------------------

def test_get_vm_not_found(client: TestClient, patch_libvirt, mock_conn):
    """GET /vms/{name} returns 404 when domain doesn't exist."""
    mock_conn.lookupByName.side_effect = libvirt.libvirtError("Domain not found")

    resp = client.get("/vms/ghost-vm")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 4. POST /provision — happy path (DHCP)
# ---------------------------------------------------------------------------

def test_provision_happy_path_dhcp(
    client: TestClient, patch_libvirt, mock_conn, tmp_path, tmp_settings
):
    """POST /provision with DHCP mode returns 201 with vm_name, status, ip."""
    mock_domain = _make_mock_domain("new-vm", vnc_port=5902)

    # Name uniqueness: first call raises (not found), second succeeds (domain appeared)
    mock_conn.lookupByName.side_effect = [
        libvirt.libvirtError("not found"),  # uniqueness check
        mock_domain,                         # poll after provision
    ]

    # Pool lookup — clear side_effect set by conftest, then set return_value
    mock_pool = MagicMock()
    mock_pool.isActive.return_value = True
    mock_pool.info.return_value = [1, 500 * 1024**3, 10 * 1024**3, 490 * 1024**3]
    mock_pool.XMLDesc.return_value = "<pool type='dir'><target><path>/mnt/pool</path></target></pool>"
    mock_pool.refresh = MagicMock()
    mock_conn.storagePoolLookupByName.side_effect = None
    mock_conn.storagePoolLookupByName.return_value = mock_pool

    fake_proc = MagicMock()
    fake_proc.stdout = "VM provisioned"
    fake_proc.returncode = 0

    seed_ud = str(tmp_path / "new-vm-user-data.yaml")
    seed_nc = None

    with (
        patch(BASE_IMG_EXISTS_PATCH, return_value=True),
        patch(SUBPROCESS_PATCH, return_value=fake_proc) as mock_sub,
        patch("api.services.cloudinit_service.write_seed_inputs", return_value=(seed_ud, seed_nc)),
        patch("api.services.cloudinit_service.render_user_data", return_value="#cloud-config\n"),
        patch(SETTINGS_DEFAULT_POOL_PATCH, return_value="default"),
        patch("api.services.vm_service.time") as mock_time,
    ):
        mock_time.time.side_effect = [0, 0, 200]  # deadline check passes, then poll exits
        mock_time.sleep = MagicMock()

        resp = client.post("/vms/provision", json={
            "vm_name": "new-vm",
            "ubuntu_version": "2204",
            "cpu": 2,
            "ram_mb": 2048,
            "disk_gb": 20,
            "ssh_public_key": "ssh-rsa AAAA...",
            "network": "public",
            "ip_mode": "dhcp",
        })

    assert resp.status_code == 201
    data = resp.json()
    assert data["vm_name"] == "new-vm"
    assert data["status"] == "provisioned"
    assert data["network"] == "public"
    assert data["ip_mode"] == "dhcp"
    assert data["vnc_port"] == 5902

    # Verify script was called with correct positional args
    call_args = mock_sub.call_args[0][0]
    assert call_args[0] == "sudo"
    assert "provision-vm.sh" in call_args[1]
    assert call_args[2] == "new-vm"           # vm_name
    assert "ubuntu-2204-base.img" in call_args[3]  # base_img_path
    assert "new-vm.qcow2" in call_args[4]     # disk_path
    assert call_args[5] == "20"               # disk_gb
    assert call_args[6] == "2"                # cpu
    assert call_args[7] == "2048"             # ram_mb
    assert call_args[8] == "network=public"   # network_arg
    assert call_args[9] == "ubuntu22.04"      # os_variant
    assert call_args[10] == seed_ud           # userdata_path
    # no networkconfig_path for DHCP
    assert len(call_args) == 11


def test_provision_macvtap_network_arg(
    client: TestClient, patch_libvirt, mock_conn, tmp_path, tmp_settings
):
    """POST /provision with network=macvtap passes correct --network to script."""
    mock_domain = _make_mock_domain("mac-vm")
    mock_conn.lookupByName.side_effect = [
        libvirt.libvirtError("not found"),
        mock_domain,
    ]
    mock_pool = MagicMock()
    mock_pool.isActive.return_value = True
    mock_pool.info.return_value = [1, 500 * 1024**3, 10 * 1024**3, 490 * 1024**3]
    mock_pool.XMLDesc.return_value = "<pool type='dir'><target><path>/mnt/pool</path></target></pool>"
    mock_pool.refresh = MagicMock()
    mock_conn.storagePoolLookupByName.side_effect = None
    mock_conn.storagePoolLookupByName.return_value = mock_pool

    fake_proc = MagicMock()
    fake_proc.stdout = ""
    fake_proc.returncode = 0

    seed_ud = str(tmp_path / "mac-vm-user-data.yaml")

    with (
        patch(BASE_IMG_EXISTS_PATCH, return_value=True),
        patch(SUBPROCESS_PATCH, return_value=fake_proc) as mock_sub,
        patch("api.services.cloudinit_service.write_seed_inputs", return_value=(seed_ud, None)),
        patch("api.services.cloudinit_service.render_user_data", return_value="#cloud-config\n"),
        patch(SETTINGS_DEFAULT_POOL_PATCH, return_value="default"),
        patch("api.services.vm_service.time") as mock_time,
    ):
        mock_time.time.side_effect = [0, 200]
        mock_time.sleep = MagicMock()

        resp = client.post("/vms/provision", json={
            "vm_name": "mac-vm",
            "ubuntu_version": "2404",
            "cpu": 1,
            "ram_mb": 1024,
            "disk_gb": 10,
            "ssh_public_key": "ssh-rsa AAAA...",
            "network": "macvtap",
            "ip_mode": "dhcp",
        })

    assert resp.status_code == 201
    call_args = mock_sub.call_args[0][0]
    network_arg = call_args[8]
    assert "type=direct" in network_arg
    assert "enp4s0" in network_arg
    assert "bridge" in network_arg


# ---------------------------------------------------------------------------
# 5. POST /provision — validation errors
# ---------------------------------------------------------------------------

def test_provision_duplicate_name_returns_409(
    client: TestClient, patch_libvirt, mock_conn, tmp_settings
):
    """POST /provision with an existing VM name returns 409."""
    existing = _make_mock_domain("existing-vm")
    mock_conn.lookupByName.return_value = existing

    resp = client.post("/vms/provision", json={
        "vm_name": "existing-vm",
        "ubuntu_version": "2204",
        "cpu": 1,
        "ram_mb": 1024,
        "disk_gb": 10,
        "ssh_public_key": "ssh-rsa AAAA...",
    })
    assert resp.status_code == 409


def test_provision_missing_base_image_returns_400(
    client: TestClient, patch_libvirt, mock_conn, tmp_settings
):
    """POST /provision when base image is missing returns 400."""
    mock_conn.lookupByName.side_effect = libvirt.libvirtError("not found")
    mock_pool = MagicMock()
    mock_pool.isActive.return_value = True
    mock_pool.info.return_value = [1, 500 * 1024**3, 10 * 1024**3, 490 * 1024**3]
    mock_pool.XMLDesc.return_value = "<pool type='dir'><target><path>/mnt/pool</path></target></pool>"
    mock_conn.storagePoolLookupByName.side_effect = None
    mock_conn.storagePoolLookupByName.return_value = mock_pool

    with (
        patch(BASE_IMG_EXISTS_PATCH, return_value=False),
        patch(SETTINGS_DEFAULT_POOL_PATCH, return_value="default"),
    ):
        resp = client.post("/vms/provision", json={
            "vm_name": "new-vm",
            "ubuntu_version": "2204",
            "cpu": 1,
            "ram_mb": 1024,
            "disk_gb": 10,
            "ssh_public_key": "ssh-rsa AAAA...",
        })
    assert resp.status_code == 400
    assert "base image" in resp.json()["detail"].lower()


def test_provision_bad_vm_name_returns_422(client: TestClient, patch_libvirt, mock_conn):
    """POST /provision with invalid vm_name returns 422."""
    resp = client.post("/vms/provision", json={
        "vm_name": "My VM!",  # uppercase + spaces — invalid
        "ubuntu_version": "2204",
        "cpu": 1,
        "ram_mb": 1024,
        "disk_gb": 10,
        "ssh_public_key": "ssh-rsa AAAA...",
    })
    assert resp.status_code == 422


def test_provision_static_ip_mode_without_static_ip_returns_422(
    client: TestClient, patch_libvirt, mock_conn
):
    """POST /provision with ip_mode=static but missing static_ip returns 422."""
    resp = client.post("/vms/provision", json={
        "vm_name": "static-vm",
        "ubuntu_version": "2204",
        "cpu": 1,
        "ram_mb": 1024,
        "disk_gb": 10,
        "ssh_public_key": "ssh-rsa AAAA...",
        "ip_mode": "static",
        "gateway": "192.168.1.1",
        # static_ip missing
    })
    assert resp.status_code == 422


def test_provision_static_ip_mode_without_gateway_returns_422(
    client: TestClient, patch_libvirt, mock_conn
):
    """POST /provision with ip_mode=static but missing gateway returns 422."""
    resp = client.post("/vms/provision", json={
        "vm_name": "static-vm",
        "ubuntu_version": "2204",
        "cpu": 1,
        "ram_mb": 1024,
        "disk_gb": 10,
        "ssh_public_key": "ssh-rsa AAAA...",
        "ip_mode": "static",
        "static_ip": "192.168.1.50",
        # gateway missing
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 6. POST /provision — static IP passes network-config as 10th arg
# ---------------------------------------------------------------------------

def test_provision_static_ip_passes_networkconfig_arg(
    client: TestClient, patch_libvirt, mock_conn, tmp_path, tmp_settings
):
    """POST /provision with static IP passes networkconfig_path as 10th script arg."""
    mock_domain = _make_mock_domain("static-vm")
    mock_conn.lookupByName.side_effect = [
        libvirt.libvirtError("not found"),
        mock_domain,
    ]
    mock_pool = MagicMock()
    mock_pool.isActive.return_value = True
    mock_pool.info.return_value = [1, 500 * 1024**3, 10 * 1024**3, 490 * 1024**3]
    mock_pool.XMLDesc.return_value = "<pool type='dir'><target><path>/mnt/pool</path></target></pool>"
    mock_pool.refresh = MagicMock()
    mock_conn.storagePoolLookupByName.side_effect = None
    mock_conn.storagePoolLookupByName.return_value = mock_pool

    fake_proc = MagicMock()
    fake_proc.stdout = ""
    fake_proc.returncode = 0

    seed_ud = str(tmp_path / "static-vm-user-data.yaml")
    seed_nc = str(tmp_path / "static-vm-network-config.yaml")

    with (
        patch(BASE_IMG_EXISTS_PATCH, return_value=True),
        patch(SUBPROCESS_PATCH, return_value=fake_proc) as mock_sub,
        patch("api.services.cloudinit_service.write_seed_inputs", return_value=(seed_ud, seed_nc)),
        patch("api.services.cloudinit_service.render_user_data", return_value="#cloud-config\n"),
        patch("api.services.cloudinit_service.render_network_config", return_value="version: 2\n"),
        patch(SETTINGS_DEFAULT_POOL_PATCH, return_value="default"),
        patch("api.services.vm_service.time") as mock_time,
    ):
        mock_time.time.side_effect = [0, 200]
        mock_time.sleep = MagicMock()

        resp = client.post("/vms/provision", json={
            "vm_name": "static-vm",
            "ubuntu_version": "2204",
            "cpu": 2,
            "ram_mb": 2048,
            "disk_gb": 20,
            "ssh_public_key": "ssh-rsa AAAA...",
            "network": "public",
            "ip_mode": "static",
            "static_ip": "192.168.1.50",
            "subnet_mask": "255.255.255.0",
            "gateway": "192.168.1.1",
            "dns": "8.8.8.8",
        })

    assert resp.status_code == 201
    call_args = mock_sub.call_args[0][0]
    # 10th arg (index 10) is userdata, 11th (index 11) is networkconfig
    assert len(call_args) == 12
    assert call_args[11] == seed_nc


# ---------------------------------------------------------------------------
# 7. mask_to_prefix tests
# ---------------------------------------------------------------------------

def test_mask_to_prefix_24():
    assert mask_to_prefix("255.255.255.0") == 24


def test_mask_to_prefix_16():
    assert mask_to_prefix("255.255.0.0") == 16


def test_mask_to_prefix_8():
    assert mask_to_prefix("255.0.0.0") == 8


def test_mask_to_prefix_32():
    assert mask_to_prefix("255.255.255.255") == 32


def test_mask_to_prefix_0():
    assert mask_to_prefix("0.0.0.0") == 0


def test_mask_to_prefix_28():
    assert mask_to_prefix("255.255.255.240") == 28


def test_mask_to_prefix_invalid_raises():
    with pytest.raises(ValueError):
        mask_to_prefix("999.999.999.999")


def test_mask_to_prefix_non_contiguous_raises():
    with pytest.raises(ValueError):
        mask_to_prefix("255.0.255.0")


def test_mask_to_prefix_bad_format_raises():
    with pytest.raises(ValueError):
        mask_to_prefix("not-a-mask")


# ---------------------------------------------------------------------------
# 8. POST /vms/{name}/start
# ---------------------------------------------------------------------------

def test_start_vm(client: TestClient, patch_libvirt, mock_conn):
    """POST /vms/{name}/start calls domain.create()."""
    domain = _make_mock_domain("stopped-vm", state=libvirt.VIR_DOMAIN_SHUTOFF)
    mock_conn.lookupByName.return_value = domain

    resp = client.post("/vms/stopped-vm/start")
    assert resp.status_code == 200
    domain.create.assert_called_once()


def test_start_vm_not_found(client: TestClient, patch_libvirt, mock_conn):
    """POST /vms/{name}/start returns 404 for missing VM."""
    mock_conn.lookupByName.side_effect = libvirt.libvirtError("not found")
    resp = client.post("/vms/ghost/start")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 9. POST /vms/{name}/stop
# ---------------------------------------------------------------------------

def test_stop_vm(client: TestClient, patch_libvirt, mock_conn):
    """POST /vms/{name}/stop calls domain.shutdown()."""
    domain = _make_mock_domain("running-vm")
    mock_conn.lookupByName.return_value = domain

    resp = client.post("/vms/running-vm/stop")
    assert resp.status_code == 200
    domain.shutdown.assert_called_once()


# ---------------------------------------------------------------------------
# 10. POST /vms/{name}/restart
# ---------------------------------------------------------------------------

def test_restart_vm(client: TestClient, patch_libvirt, mock_conn):
    """POST /vms/{name}/restart calls domain.reboot(0)."""
    domain = _make_mock_domain("running-vm")
    mock_conn.lookupByName.return_value = domain

    resp = client.post("/vms/running-vm/restart")
    assert resp.status_code == 200
    domain.reboot.assert_called_once_with(0)


# ---------------------------------------------------------------------------
# 11. DELETE /vms/{name}
# ---------------------------------------------------------------------------

def test_delete_vm_running(client: TestClient, patch_libvirt, mock_conn):
    """DELETE /vms/{name} calls destroy() then undefineFlags() then vol.delete() × 2."""
    domain = _make_mock_domain("running-vm", state=libvirt.VIR_DOMAIN_RUNNING)
    mock_conn.lookupByName.return_value = domain

    # Mock vol lookups
    mock_vol1 = MagicMock()
    mock_vol2 = MagicMock()
    mock_conn.storageVolLookupByPath.side_effect = [mock_vol1, mock_vol2]

    resp = client.delete("/vms/running-vm")
    assert resp.status_code == 204
    domain.destroy.assert_called_once()
    # undefineFlags or undefine should be called
    assert domain.undefineFlags.called or domain.undefine.called
    # vol.delete() called for each disk path found in XML
    assert mock_vol1.delete.called or mock_vol2.delete.called


def test_delete_vm_stopped(client: TestClient, patch_libvirt, mock_conn):
    """DELETE /vms/{name} on stopped VM does NOT call destroy()."""
    domain = _make_mock_domain("stopped-vm", state=libvirt.VIR_DOMAIN_SHUTOFF)
    mock_conn.lookupByName.return_value = domain
    mock_conn.storageVolLookupByPath.side_effect = libvirt.libvirtError("not found")

    resp = client.delete("/vms/stopped-vm")
    assert resp.status_code == 204
    domain.destroy.assert_not_called()


def test_delete_vm_not_found(client: TestClient, patch_libvirt, mock_conn):
    """DELETE /vms/{name} returns 404 when domain doesn't exist."""
    mock_conn.lookupByName.side_effect = libvirt.libvirtError("Domain not found")
    resp = client.delete("/vms/ghost")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 12. PATCH /vms/{name}/resize — CPU+RAM on running VM → 409
# ---------------------------------------------------------------------------

def test_resize_cpu_ram_on_running_vm_returns_409(
    client: TestClient, patch_libvirt, mock_conn
):
    """PATCH /vms/{name}/resize with cpu+ram on running VM returns 409."""
    domain = _make_mock_domain("running-vm", state=libvirt.VIR_DOMAIN_RUNNING)
    mock_conn.lookupByName.return_value = domain

    resp = client.patch("/vms/running-vm/resize", json={"cpu": 4, "ram_mb": 4096})
    assert resp.status_code == 409
    domain.setVcpusFlags.assert_not_called()
    domain.setMemoryFlags.assert_not_called()


def test_resize_cpu_only_on_running_vm_returns_409(
    client: TestClient, patch_libvirt, mock_conn
):
    """PATCH resize with only cpu on running VM also returns 409."""
    domain = _make_mock_domain("running-vm", state=libvirt.VIR_DOMAIN_RUNNING)
    mock_conn.lookupByName.return_value = domain

    resp = client.patch("/vms/running-vm/resize", json={"cpu": 4})
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# 13. PATCH /vms/{name}/resize — CPU+RAM on stopped VM succeeds
# ---------------------------------------------------------------------------

def test_resize_cpu_ram_on_stopped_vm_succeeds(
    client: TestClient, patch_libvirt, mock_conn
):
    """PATCH /vms/{name}/resize with cpu+ram on stopped VM calls setVcpusFlags + setMemoryFlags."""
    domain = _make_mock_domain("stopped-vm", state=libvirt.VIR_DOMAIN_SHUTOFF)
    mock_conn.lookupByName.return_value = domain

    resp = client.patch("/vms/stopped-vm/resize", json={"cpu": 4, "ram_mb": 4096})
    assert resp.status_code == 200
    domain.setVcpusFlags.assert_called_once_with(4, libvirt.VIR_DOMAIN_AFFECT_CONFIG)
    # setMemoryFlags called twice (max + current)
    assert domain.setMemoryFlags.call_count == 2


def test_resize_disk_on_running_vm_succeeds(
    client: TestClient, patch_libvirt, mock_conn
):
    """PATCH resize with disk_gb only can be done on running VM."""
    domain = _make_mock_domain("running-vm", state=libvirt.VIR_DOMAIN_RUNNING)
    mock_conn.lookupByName.return_value = domain

    resp = client.patch("/vms/running-vm/resize", json={"disk_gb": 50})
    assert resp.status_code == 200
    domain.blockResize.assert_called_once()
    call_args = domain.blockResize.call_args[0]
    assert call_args[0] == "vda"
    assert call_args[1] == 50 * 1024 ** 3


# ---------------------------------------------------------------------------
# 14. PATCH /vms/{name}/network — returns message mentioning restart
# ---------------------------------------------------------------------------

def test_update_network_returns_restart_message(
    client: TestClient, patch_libvirt, mock_conn
):
    """PATCH /vms/{name}/network returns message containing 'restart'."""
    domain = _make_mock_domain("my-vm")
    mock_conn.lookupByName.return_value = domain

    resp = client.patch("/vms/my-vm/network", json={"network": "internal"})
    assert resp.status_code == 200
    data = resp.json()
    assert "restart" in data["message"].lower()
    assert data["network"] == "internal"


def test_update_network_not_found(client: TestClient, patch_libvirt, mock_conn):
    """PATCH /vms/{name}/network returns 404 for unknown VM."""
    mock_conn.lookupByName.side_effect = libvirt.libvirtError("not found")
    resp = client.patch("/vms/ghost/network", json={"network": "internal"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 15. GET /vms/{name}/console — returns vnc_port
# ---------------------------------------------------------------------------

def test_console_returns_vnc_port(
    client: TestClient, patch_libvirt, mock_conn, tmp_path, monkeypatch
):
    """GET /vms/{name}/console returns vnc_port + token and writes a token file."""
    monkeypatch.setattr(config, "NOVNC_TOKEN_DIR", str(tmp_path))
    domain = _make_mock_domain("running-vm", vnc_port=5903)
    mock_conn.lookupByName.return_value = domain

    resp = client.get("/vms/running-vm/console")
    assert resp.status_code == 200
    body = resp.json()
    assert body["vnc_port"] == 5903
    assert body["token"] == "running-vm"
    token_file = tmp_path / "running-vm"
    assert token_file.read_text().strip() == "running-vm: 127.0.0.1:5903"


def test_console_not_found(client: TestClient, patch_libvirt, mock_conn):
    """GET /vms/{name}/console returns 404 for missing VM."""
    mock_conn.lookupByName.side_effect = libvirt.libvirtError("not found")
    resp = client.get("/vms/ghost/console")
    assert resp.status_code == 404


def test_console_no_vnc_returns_400(client: TestClient, patch_libvirt, mock_conn):
    """GET /vms/{name}/console returns 400 when VM has no VNC graphics."""
    domain = MagicMock()
    domain.name.return_value = "no-vnc-vm"
    domain.XMLDesc.return_value = "<domain><devices></devices></domain>"
    mock_conn.lookupByName.return_value = domain

    resp = client.get("/vms/no-vnc-vm/console")
    assert resp.status_code == 400

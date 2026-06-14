"""Tests for template_service and the /templates + /vms/{name}/snapshots/{snap}/export routes.

All libvirt and subprocess calls are mocked — no real hypervisor needed.
"""
from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import libvirt
import pytest
from fastapi.testclient import TestClient

from api import config
from api.services import template_service


# ---------------------------------------------------------------------------
# Domain XML fixtures
# ---------------------------------------------------------------------------

def _make_domain_xml(
    vm_name: str = "test-vm",
    disk_path: str = "/mnt/nvme1/kvm/pool/vms/test-vm.qcow2",
) -> str:
    return f"""<domain type='kvm'>
  <name>{vm_name}</name>
  <os>
    <type arch='x86_64' machine='pc-i440fx-6.2'>hvm</type>
  </os>
  <devices>
    <disk type='file' device='disk'>
      <source file='{disk_path}'/>
      <target dev='vda' bus='virtio'/>
    </disk>
    <disk type='file' device='cdrom'>
      <source file='/home/naim/kvmify/seeds/{vm_name}-seed.iso'/>
      <target dev='sda' bus='sata'/>
    </disk>
  </devices>
</domain>"""


def _make_mock_domain(
    vm_name: str = "test-vm",
    disk_path: str = "/mnt/nvme1/kvm/pool/vms/test-vm.qcow2",
) -> MagicMock:
    domain = MagicMock(name=f"virDomain:{vm_name}")
    domain.name.return_value = vm_name
    domain.XMLDesc.return_value = _make_domain_xml(vm_name, disk_path)
    return domain


# ---------------------------------------------------------------------------
# Helper: create a mock subprocess.run that also writes the dest qcow2 file
# ---------------------------------------------------------------------------

def _make_fake_run(dest_content: bytes = b"fake qcow2 data"):
    """Return a fake subprocess.run that creates the dest file (5th arg, index 4).

    The export command is: ["sudo", EXPORT_SCRIPT, src_disk, snap_name, dest_qcow2]
    """
    def _fake_run(cmd, *args, **kwargs):
        dest = cmd[4]  # ["sudo", EXPORT_SCRIPT, src_disk, snap_name, dest_qcow2]
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(dest_content)
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = "Exported\n"
        proc.stderr = ""
        return proc
    return _fake_run


# ---------------------------------------------------------------------------
# Unit tests: template_service._primary_disk_path
# ---------------------------------------------------------------------------

class TestPrimaryDiskPath:
    def test_returns_first_file_disk_path(self):
        xml = _make_domain_xml("vm", "/mnt/nvme1/kvm/pool/vms/vm.qcow2")
        path = template_service._primary_disk_path(xml)
        assert path == "/mnt/nvme1/kvm/pool/vms/vm.qcow2"

    def test_skips_cdrom(self):
        # Only a cdrom disk — should raise
        xml = """<domain><devices>
          <disk type='file' device='cdrom'>
            <source file='/tmp/seed.iso'/>
          </disk>
        </devices></domain>"""
        with pytest.raises(ValueError, match="No usable"):
            template_service._primary_disk_path(xml)

    def test_no_disk_raises(self):
        xml = "<domain><devices></devices></domain>"
        with pytest.raises(ValueError, match="No usable"):
            template_service._primary_disk_path(xml)

    def test_bad_xml_raises(self):
        with pytest.raises(ValueError, match="parse"):
            template_service._primary_disk_path("not xml <<<")

    def test_resolves_block_disk_dev(self):
        xml = """<domain><devices>
          <disk type='block' device='disk'>
            <source dev='/dev/vg0/vm-lv'/>
          </disk>
        </devices></domain>"""
        assert template_service._primary_disk_path(xml) == "/dev/vg0/vm-lv"

    def test_resolves_volume_disk_via_storage_api(self):
        # A pool/volume-backed disk (as used by virsh vol-based VMs, e.g. sandbox)
        xml = """<domain><devices>
          <disk type='volume' device='disk'>
            <source pool='default' volume='sandbox-root'/>
          </disk>
        </devices></domain>"""
        from unittest.mock import MagicMock
        conn = MagicMock()
        vol = MagicMock()
        vol.path.return_value = "/mnt/nvme1/kvm/pool/sandbox-root"
        conn.storagePoolLookupByName.return_value.storageVolLookupByName.return_value = vol
        path = template_service._primary_disk_path(xml, conn)
        assert path == "/mnt/nvme1/kvm/pool/sandbox-root"
        conn.storagePoolLookupByName.assert_called_once_with("default")

    def test_volume_disk_without_conn_raises(self):
        xml = """<domain><devices>
          <disk type='volume' device='disk'>
            <source pool='default' volume='sandbox-root'/>
          </disk>
        </devices></domain>"""
        with pytest.raises(ValueError, match="without a libvirt connection"):
            template_service._primary_disk_path(xml)


# ---------------------------------------------------------------------------
# Unit tests: template_service._validate_name
# ---------------------------------------------------------------------------

class TestValidateName:
    def test_valid_names(self):
        for name in ["a", "abc", "my-template", "ubuntu2204-base", "a" * 64]:
            template_service._validate_name(name)  # should not raise

    def test_invalid_names(self):
        for name in ["A", "-bad", "has space", "under_score", "", "a" * 65]:
            with pytest.raises(ValueError):
                template_service._validate_name(name)

    def test_leading_digit_valid(self):
        template_service._validate_name("1abc")

    def test_leading_hyphen_invalid(self):
        with pytest.raises(ValueError):
            template_service._validate_name("-bad")

    def test_uppercase_invalid(self):
        with pytest.raises(ValueError):
            template_service._validate_name("MyTemplate")

    def test_too_long_invalid(self):
        with pytest.raises(ValueError):
            template_service._validate_name("a" * 65)


# ---------------------------------------------------------------------------
# Unit tests: template_service.export_from_snapshot
# ---------------------------------------------------------------------------

class TestExportFromSnapshot:
    def test_export_success(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))

        mock_conn = MagicMock()
        mock_domain = _make_mock_domain("test-vm")
        mock_domain.snapshotLookupByName.return_value = MagicMock()
        mock_conn.lookupByName.return_value = mock_domain

        with patch(
            "api.services.template_service.libvirt_service.get_domain",
            return_value=mock_domain,
        ), patch(
            "api.services.template_service.subprocess.run",
            side_effect=_make_fake_run(),
        ):
            result = template_service.export_from_snapshot(
                mock_conn, "test-vm", "snap1", "my-template"
            )

        assert result["name"] == "my-template"
        assert result["source_vm"] == "test-vm"
        assert result["source_snapshot"] == "snap1"
        assert result["os_variant"] == "ubuntu22.04"
        assert result["size"] is not None
        assert result["created"] is not None
        # Sidecar JSON should exist
        json_path = tmp_path / "my-template.json"
        assert json_path.exists()
        meta = json.loads(json_path.read_text())
        assert meta["source_vm"] == "test-vm"

    def test_export_duplicate_raises_file_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))
        # Pre-create the qcow2 file
        (tmp_path / "dup-tpl.qcow2").write_bytes(b"existing")

        with pytest.raises(FileExistsError, match="already exists"):
            template_service.export_from_snapshot(
                MagicMock(), "vm", "snap", "dup-tpl"
            )

    def test_export_missing_snapshot_raises_lookup_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))

        mock_conn = MagicMock()
        mock_domain = _make_mock_domain("test-vm")
        mock_domain.snapshotLookupByName.side_effect = libvirt.libvirtError("not found")

        with patch(
            "api.services.template_service.libvirt_service.get_domain",
            return_value=mock_domain,
        ):
            with pytest.raises(LookupError, match="not found"):
                template_service.export_from_snapshot(
                    mock_conn, "test-vm", "ghost-snap", "tpl"
                )

    def test_export_invalid_name_raises_value_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))
        with pytest.raises(ValueError, match="Invalid template name"):
            template_service.export_from_snapshot(
                MagicMock(), "vm", "snap", "INVALID_NAME"
            )

    def test_export_script_failure_raises_runtime_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))

        mock_conn = MagicMock()
        mock_domain = _make_mock_domain("test-vm")
        mock_domain.snapshotLookupByName.return_value = MagicMock()

        import subprocess
        failing_proc = MagicMock()
        failing_proc.returncode = 1
        failing_proc.stderr = "qemu-img error"
        failing_proc.stdout = ""

        with patch(
            "api.services.template_service.libvirt_service.get_domain",
            return_value=mock_domain,
        ), patch(
            "api.services.template_service.subprocess.run",
            side_effect=subprocess.CalledProcessError(
                1, "export-vm-snapshot.sh", stderr="qemu-img error"
            ),
        ):
            with pytest.raises(RuntimeError, match="Export script failed"):
                template_service.export_from_snapshot(
                    mock_conn, "test-vm", "snap1", "fail-tpl"
                )


# ---------------------------------------------------------------------------
# Unit tests: template_service.list_templates
# ---------------------------------------------------------------------------

class TestListTemplates:
    def test_empty_when_dir_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path / "nonexistent"))
        assert template_service.list_templates() == []

    def test_lists_qcow2_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))
        # Create two templates with sidecars
        for name in ["alpha", "beta"]:
            (tmp_path / f"{name}.qcow2").write_bytes(b"x" * 1024)
            sidecar = {
                "name": name,
                "source_vm": "vm1",
                "source_snapshot": "snap1",
                "os_variant": "ubuntu22.04",
                "created": "2025-01-01T00:00:00+00:00",
            }
            (tmp_path / f"{name}.json").write_text(json.dumps(sidecar))

        items = template_service.list_templates()
        assert len(items) == 2
        names = {i["name"] for i in items}
        assert names == {"alpha", "beta"}
        for item in items:
            assert item["source_vm"] == "vm1"
            assert item["os_variant"] == "ubuntu22.04"
            assert item["size"] == 1024

    def test_handles_missing_sidecar_gracefully(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))
        (tmp_path / "orphan.qcow2").write_bytes(b"data")
        # No JSON sidecar
        items = template_service.list_templates()
        assert len(items) == 1
        item = items[0]
        assert item["name"] == "orphan"
        assert item["source_vm"] is None

    def test_sorted_by_name(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))
        for name in ["zeta", "alpha", "mu"]:
            (tmp_path / f"{name}.qcow2").write_bytes(b"x")
        items = template_service.list_templates()
        assert [i["name"] for i in items] == ["alpha", "mu", "zeta"]


# ---------------------------------------------------------------------------
# Unit tests: template_service.delete_template
# ---------------------------------------------------------------------------

class TestDeleteTemplate:
    def test_delete_removes_qcow2_and_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))
        qcow2 = tmp_path / "my-tpl.qcow2"
        json_f = tmp_path / "my-tpl.json"
        qcow2.write_bytes(b"disk")
        json_f.write_text("{}")

        template_service.delete_template("my-tpl")
        assert not qcow2.exists()
        assert not json_f.exists()

    def test_delete_without_json_still_succeeds(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))
        (tmp_path / "tpl.qcow2").write_bytes(b"disk")
        # No JSON
        template_service.delete_template("tpl")
        assert not (tmp_path / "tpl.qcow2").exists()

    def test_delete_missing_raises_lookup_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))
        with pytest.raises(LookupError, match="not found"):
            template_service.delete_template("ghost")

    def test_delete_invalid_name_raises_value_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))
        with pytest.raises(ValueError, match="Invalid template name"):
            template_service.delete_template("INVALID")


# ---------------------------------------------------------------------------
# Router tests via TestClient: GET /templates
# ---------------------------------------------------------------------------

class TestTemplatesRouter:
    def test_list_templates_empty(self, client: TestClient, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path / "nonexistent"))
        resp = client.get("/templates")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_templates_returns_items(self, client: TestClient, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))
        (tmp_path / "tpl1.qcow2").write_bytes(b"x" * 512)
        sidecar = {
            "name": "tpl1",
            "source_vm": "vm1",
            "source_snapshot": "snap1",
            "os_variant": "ubuntu22.04",
            "created": "2025-06-01T00:00:00+00:00",
        }
        (tmp_path / "tpl1.json").write_text(json.dumps(sidecar))

        resp = client.get("/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "tpl1"
        assert data[0]["source_vm"] == "vm1"

    def test_delete_template_success(self, client: TestClient, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))
        (tmp_path / "del-me.qcow2").write_bytes(b"disk")

        resp = client.delete("/templates/del-me")
        assert resp.status_code == 204
        assert not (tmp_path / "del-me.qcow2").exists()

    def test_delete_template_not_found_returns_404(
        self, client: TestClient, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))
        resp = client.delete("/templates/ghost")
        assert resp.status_code == 404

    def test_delete_template_invalid_name_returns_400(
        self, client: TestClient, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))
        resp = client.delete("/templates/INVALID-NAME")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Router tests via TestClient: POST /vms/{name}/snapshots/{snap}/export
# ---------------------------------------------------------------------------

class TestExportSnapshotRoute:
    def test_export_success_returns_201(
        self, client: TestClient, patch_libvirt, mock_conn, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))

        mock_domain = _make_mock_domain("my-vm")
        mock_domain.snapshotLookupByName.return_value = MagicMock()
        mock_conn.lookupByName.return_value = mock_domain

        with patch(
            "api.services.template_service.subprocess.run",
            side_effect=_make_fake_run(),
        ):
            resp = client.post(
                "/vms/my-vm/snapshots/snap1/export",
                json={"template_name": "my-template"},
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "my-template"
        assert data["source_vm"] == "my-vm"
        assert data["source_snapshot"] == "snap1"
        assert data["size"] is not None

    def test_export_duplicate_name_returns_409(
        self, client: TestClient, patch_libvirt, mock_conn, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))
        # Pre-create the qcow2
        (tmp_path / "dup.qcow2").write_bytes(b"exists")

        mock_domain = _make_mock_domain("my-vm")
        mock_conn.lookupByName.return_value = mock_domain

        resp = client.post(
            "/vms/my-vm/snapshots/snap1/export",
            json={"template_name": "dup"},
        )
        assert resp.status_code == 409

    def test_export_missing_snapshot_returns_404(
        self, client: TestClient, patch_libvirt, mock_conn, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))

        mock_domain = _make_mock_domain("my-vm")
        mock_domain.snapshotLookupByName.side_effect = libvirt.libvirtError("not found")
        mock_conn.lookupByName.return_value = mock_domain

        resp = client.post(
            "/vms/my-vm/snapshots/ghost-snap/export",
            json={"template_name": "new-tpl"},
        )
        assert resp.status_code == 404

    def test_export_missing_vm_returns_400(
        self, client: TestClient, patch_libvirt, mock_conn, tmp_path, monkeypatch
    ):
        """Missing VM raises ValueError (from libvirt_service.get_domain) → 400."""
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))
        mock_conn.lookupByName.side_effect = libvirt.libvirtError("Domain not found")

        resp = client.post(
            "/vms/ghost-vm/snapshots/snap1/export",
            json={"template_name": "new-tpl"},
        )
        # ValueError from get_domain → mapped to 400 by the export route
        assert resp.status_code == 400

    def test_export_invalid_template_name_returns_422(
        self, client: TestClient, patch_libvirt, mock_conn
    ):
        """Template name validation via Pydantic pattern → 422."""
        resp = client.post(
            "/vms/my-vm/snapshots/snap1/export",
            json={"template_name": "INVALID NAME!"},
        )
        assert resp.status_code == 422

    def test_export_script_failure_returns_500(
        self, client: TestClient, patch_libvirt, mock_conn, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(config, "TEMPLATES_DIR", str(tmp_path))

        mock_domain = _make_mock_domain("my-vm")
        mock_domain.snapshotLookupByName.return_value = MagicMock()
        mock_conn.lookupByName.return_value = mock_domain

        import subprocess
        with patch(
            "api.services.template_service.subprocess.run",
            side_effect=subprocess.CalledProcessError(
                1, "export-vm-snapshot.sh", stderr="qemu-img: error"
            ),
        ):
            resp = client.post(
                "/vms/my-vm/snapshots/snap1/export",
                json={"template_name": "fail-tpl"},
            )
        assert resp.status_code == 500

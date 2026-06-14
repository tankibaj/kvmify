"""Template service — export VM snapshots as standalone qcow2 templates.

Templates are flattened qcow2 images stored in TEMPLATES_DIR.  They are
independent of the source VM/disk/snapshot and can be used as backing images
when provisioning new VMs.

This module does NOT touch snapshot_service — rollback snapshots are unchanged.
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional

from api import config
from api.services import libvirt_service

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,63}$")


def _validate_name(name: str) -> None:
    """Enforce template naming rules. Raises ValueError on bad name."""
    if not _NAME_RE.match(name):
        raise ValueError(
            f"Invalid template name '{name}': must match ^[a-z0-9][a-z0-9\\-]{{0,63}}$"
        )


def _template_paths(name: str) -> tuple[str, str]:
    """Return (qcow2_path, json_path) for a given template name."""
    base = os.path.join(config.TEMPLATES_DIR, name)
    return f"{base}.qcow2", f"{base}.json"


def _primary_disk_path(xml_desc: str, conn=None) -> str:
    """Parse domain XML and return the first non-cdrom disk's backing file path.

    Handles all three libvirt disk source types:
    - type='file'   -> <source file=...>
    - type='block'  -> <source dev=...>
    - type='volume' -> <source pool=... volume=...>, resolved to a path via the
                       libvirt storage API (requires ``conn``).

    Raises:
        ValueError: if no suitable disk source is found or a volume cannot be
            resolved (e.g. no connection supplied).
    """
    try:
        root = ET.fromstring(xml_desc)
    except ET.ParseError as exc:
        raise ValueError(f"Failed to parse domain XML: {exc}") from exc

    for disk in root.findall("./devices/disk"):
        if disk.get("device") == "cdrom":
            continue
        source = disk.find("source")
        if source is None:
            continue

        dtype = disk.get("type")
        if dtype == "file":
            path = source.get("file")
            if path:
                return path
        elif dtype == "block":
            path = source.get("dev")
            if path:
                return path
        elif dtype == "volume":
            pool_name = source.get("pool")
            vol_name = source.get("volume")
            if pool_name and vol_name:
                if conn is None:
                    raise ValueError(
                        "Cannot resolve volume-backed disk without a libvirt "
                        "connection"
                    )
                try:
                    pool = conn.storagePoolLookupByName(pool_name)
                    vol = pool.storageVolLookupByName(vol_name)
                    return vol.path()
                except Exception as exc:  # libvirt.libvirtError
                    raise ValueError(
                        f"Failed to resolve volume '{vol_name}' in pool "
                        f"'{pool_name}': {exc}"
                    ) from exc

    raise ValueError("No usable non-cdrom disk found in domain XML")


def _mtime_iso(path: str) -> str:
    """Return the file's mtime as an ISO-8601 UTC string."""
    mtime = os.stat(path).st_mtime
    return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()


def _read_sidecar(json_path: str) -> dict:
    """Read sidecar JSON, returning empty dict on any failure."""
    try:
        with open(json_path) as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def export_from_snapshot(
    conn,
    vm_name: str,
    snap_name: str,
    template_name: str,
) -> dict:
    """Export an internal qcow2 snapshot as a standalone template.

    Steps:
    1. Validate template_name; reject if qcow2 already exists.
    2. Look up domain and snapshot (raises on missing).
    3. Resolve source disk path from domain XML.
    4. Run export-vm-snapshot.sh via sudo subprocess.
    5. Write sidecar JSON metadata.
    6. Return TemplateInfo dict.

    Raises:
        ValueError: on bad template name or domain not found.
        FileExistsError: if the template qcow2 already exists.
        LookupError: if the snapshot doesn't exist.
        RuntimeError: if the export script fails.
    """
    _validate_name(template_name)
    qcow2_path, json_path = _template_paths(template_name)

    if os.path.exists(qcow2_path):
        raise FileExistsError(
            f"Template '{template_name}' already exists at {qcow2_path}"
        )

    # Look up domain
    domain = libvirt_service.get_domain(conn, vm_name)

    # Look up snapshot — libvirtError → LookupError
    import libvirt as _libvirt
    try:
        domain.snapshotLookupByName(snap_name, 0)
    except _libvirt.libvirtError as exc:
        raise LookupError(
            f"Snapshot '{snap_name}' not found on VM '{vm_name}': {exc}"
        ) from exc

    # Resolve source disk
    xml_desc = domain.XMLDesc(0)
    source_disk = _primary_disk_path(xml_desc, conn)

    # Run the export script
    cmd = ["sudo", config.EXPORT_SCRIPT, source_disk, snap_name, qcow2_path]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Export script failed (exit {exc.returncode}):\n"
            f"{exc.stderr or exc.stdout}"
        ) from exc

    # Derive os_variant — best-effort from domain metadata
    os_variant = _derive_os_variant(xml_desc)

    # Write sidecar JSON
    created = _mtime_iso(qcow2_path)
    sidecar = {
        "name": template_name,
        "source_vm": vm_name,
        "source_snapshot": snap_name,
        "os_variant": os_variant,
        "created": created,
    }
    with open(json_path, "w") as fh:
        json.dump(sidecar, fh, indent=2)

    size = os.stat(qcow2_path).st_size
    return {
        "name": template_name,
        "size": size,
        "created": created,
        "source_vm": vm_name,
        "source_snapshot": snap_name,
        "os_variant": os_variant,
    }


def _derive_os_variant(xml_desc: str) -> str:
    """Best-effort: derive os_variant from domain XML.

    Checks <os><type> or falls back to 'ubuntu22.04'.
    """
    try:
        root = ET.fromstring(xml_desc)
        os_elem = root.find("./os/type")
        if os_elem is not None:
            machine = os_elem.get("machine", "")
            # Not useful enough — fall through to default
    except ET.ParseError:
        pass
    return "ubuntu22.04"


def list_templates() -> list[dict]:
    """List all templates in TEMPLATES_DIR, sorted by name.

    Returns empty list if TEMPLATES_DIR doesn't exist.
    """
    if not os.path.isdir(config.TEMPLATES_DIR):
        return []

    results = []
    pattern = os.path.join(config.TEMPLATES_DIR, "*.qcow2")
    for qcow2_path in sorted(glob.glob(pattern)):
        fname = os.path.basename(qcow2_path)
        name = fname[:-6]  # strip .qcow2
        _, json_path = _template_paths(name)
        sidecar = _read_sidecar(json_path)

        try:
            st = os.stat(qcow2_path)
            size = st.st_size
            created = sidecar.get("created") or _mtime_iso(qcow2_path)
        except OSError:
            size = None
            created = sidecar.get("created")

        results.append({
            "name": name,
            "size": size,
            "created": created,
            "source_vm": sidecar.get("source_vm"),
            "source_snapshot": sidecar.get("source_snapshot"),
            "os_variant": sidecar.get("os_variant"),
        })

    return results


def delete_template(name: str) -> None:
    """Delete a template's qcow2 and sidecar JSON files.

    Raises:
        ValueError: if name is invalid.
        LookupError: if the qcow2 file doesn't exist.
    """
    _validate_name(name)
    qcow2_path, json_path = _template_paths(name)

    if not os.path.exists(qcow2_path):
        raise LookupError(f"Template '{name}' not found")

    os.remove(qcow2_path)
    try:
        os.remove(json_path)
    except FileNotFoundError:
        pass

"""Snapshot business logic: list, take, restore, delete domain snapshots.

All libvirt interactions live here.  The router is thin: it calls these
functions and maps exceptions to HTTPException.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional

import libvirt

from api.services import libvirt_service


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_snapshot_xml(xml_desc: str) -> dict:
    """Parse a snapshot XML descriptor into a plain dict."""
    try:
        root = ET.fromstring(xml_desc)
    except ET.ParseError:
        return {}

    name_el = root.find("name")
    name = name_el.text if name_el is not None else None

    desc_el = root.find("description")
    description = desc_el.text if desc_el is not None else None

    created: Optional[str] = None
    ct_el = root.find("creationTime")
    if ct_el is not None and ct_el.text:
        try:
            ts = int(ct_el.text)
            created = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        except (ValueError, OSError):
            created = ct_el.text

    state: Optional[str] = None
    state_el = root.find("state")
    if state_el is not None:
        state = state_el.text

    return {
        "name": name,
        "created": created,
        "description": description,
        "state": state,
    }


# ---------------------------------------------------------------------------
# list_snapshots
# ---------------------------------------------------------------------------

def list_snapshots(conn: libvirt.virConnect, vm_name: str) -> list[dict]:
    """Return info dicts for all snapshots of a domain.

    Raises:
        ValueError: if the domain does not exist.
    """
    domain = libvirt_service.get_domain(conn, vm_name)
    snapshots = domain.listAllSnapshots()
    result: list[dict] = []
    for snap in snapshots:
        info = _parse_snapshot_xml(snap.getXMLDesc())
        is_current = False
        try:
            is_current = bool(snap.isCurrent())
        except (libvirt.libvirtError, AttributeError):
            pass
        info["is_current"] = is_current
        result.append(info)
    return result


# ---------------------------------------------------------------------------
# take_snapshot
# ---------------------------------------------------------------------------

def take_snapshot(
    conn: libvirt.virConnect,
    vm_name: str,
    name: str,
    description: Optional[str] = None,
) -> dict:
    """Create a new snapshot on a domain.

    Raises:
        ValueError: if the domain does not exist or snap name already exists.
    """
    domain = libvirt_service.get_domain(conn, vm_name)

    # Check for duplicate name
    try:
        existing = domain.snapshotLookupByName(name)
        if existing is not None:
            raise ValueError(f"Snapshot '{name}' already exists on VM '{vm_name}'")
    except libvirt.libvirtError:
        pass  # expected — snapshot not found

    desc_xml = f"<description>{description}</description>" if description else ""
    snap_xml = (
        f"<domainsnapshot>"
        f"<name>{name}</name>"
        f"{desc_xml}"
        f"</domainsnapshot>"
    )
    try:
        snap = domain.snapshotCreateXML(snap_xml, 0)
    except libvirt.libvirtError as exc:
        msg = str(exc)
        if "already exists" in msg.lower():
            raise ValueError(f"Snapshot '{name}' already exists on VM '{vm_name}'") from exc
        raise ValueError(f"Failed to create snapshot: {exc}") from exc

    info = _parse_snapshot_xml(snap.getXMLDesc())
    is_current = False
    try:
        is_current = bool(snap.isCurrent())
    except (libvirt.libvirtError, AttributeError):
        pass
    info["is_current"] = is_current
    return info


# ---------------------------------------------------------------------------
# restore_snapshot
# ---------------------------------------------------------------------------

def restore_snapshot(
    conn: libvirt.virConnect,
    vm_name: str,
    snap_name: str,
) -> None:
    """Revert a domain to a named snapshot.

    Raises:
        ValueError: if the domain does not exist.
        LookupError: if the snapshot does not exist.
    """
    domain = libvirt_service.get_domain(conn, vm_name)
    try:
        snap = domain.snapshotLookupByName(snap_name)
    except libvirt.libvirtError as exc:
        raise LookupError(
            f"Snapshot '{snap_name}' not found on VM '{vm_name}'"
        ) from exc
    try:
        domain.revertToSnapshot(snap, 0)
    except libvirt.libvirtError as exc:
        raise ValueError(f"Failed to restore snapshot: {exc}") from exc


# ---------------------------------------------------------------------------
# delete_snapshot
# ---------------------------------------------------------------------------

def delete_snapshot(
    conn: libvirt.virConnect,
    vm_name: str,
    snap_name: str,
) -> None:
    """Delete a named snapshot from a domain.

    Raises:
        ValueError: if the domain does not exist.
        LookupError: if the snapshot does not exist.
    """
    domain = libvirt_service.get_domain(conn, vm_name)
    try:
        snap = domain.snapshotLookupByName(snap_name)
    except libvirt.libvirtError as exc:
        raise LookupError(
            f"Snapshot '{snap_name}' not found on VM '{vm_name}'"
        ) from exc
    try:
        snap.delete(0)
    except libvirt.libvirtError as exc:
        raise ValueError(f"Failed to delete snapshot: {exc}") from exc

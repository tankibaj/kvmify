"""libvirt storage pool business logic.

All libvirt interactions live here.  Routers are thin: they call these
functions and map exceptions to HTTPException.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import libvirt

from api import schemas
from api.services import libvirt_service, settings_service


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pool_type_from_xml(xml_desc: str) -> str:
    """Extract the pool ``type`` attribute from its XML descriptor."""
    try:
        root = ET.fromstring(xml_desc)
        return root.attrib.get("type", "unknown")
    except ET.ParseError:
        return "unknown"


def _pool_path_from_xml(xml_desc: str) -> str:
    """Extract ``<target><path>`` from pool XML.  Returns '' if absent."""
    try:
        root = ET.fromstring(xml_desc)
        path_el = root.find("./target/path")
        return path_el.text if path_el is not None and path_el.text else ""
    except ET.ParseError:
        return ""


def _build_pool_info(pool: libvirt.virStoragePool) -> schemas.PoolInfo:
    """Convert a libvirt pool object to a :class:`~api.schemas.PoolInfo`."""
    xml_desc = pool.XMLDesc(0)
    # info() → [state_int, capacity, allocation, available]
    info = pool.info()
    state_str = "active" if pool.isActive() else "inactive"
    try:
        vol_count = pool.numOfVolumes() if pool.isActive() else 0
    except libvirt.libvirtError:
        vol_count = 0

    return schemas.PoolInfo(
        name=pool.name(),
        state=state_str,
        type=_pool_type_from_xml(xml_desc),
        capacity=info[1],
        allocation=info[2],
        available=info[3],
        autostart=bool(pool.autostart()),
        path=_pool_path_from_xml(xml_desc),
        is_default=(pool.name() == settings_service.get_default_pool()),
        volume_count=vol_count,
    )


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def list_pools(conn: libvirt.virConnect) -> list[schemas.PoolInfo]:
    """Return info for every storage pool known to libvirt."""
    pools = conn.listAllStoragePools(0)
    return [_build_pool_info(p) for p in pools]


def create_pool(conn: libvirt.virConnect, body: schemas.PoolCreate) -> schemas.PoolInfo:
    """Define, build, start, and autostart a new directory pool.

    Raises:
        ValueError: if a pool with *name* already exists or the operation fails.
    """
    # Check for duplicate
    try:
        conn.storagePoolLookupByName(body.name)
        raise ValueError(f"Pool '{body.name}' already exists")
    except libvirt.libvirtError:
        pass  # expected — pool not found

    xml = (
        f"<pool type='dir'>"
        f"<name>{body.name}</name>"
        f"<target><path>{body.path}</path></target>"
        f"</pool>"
    )
    try:
        pool = conn.storagePoolDefineXML(xml, 0)
        pool.build(0)
        pool.create(0)
        pool.setAutostart(True)
    except libvirt.libvirtError as exc:
        raise ValueError(str(exc)) from exc

    return _build_pool_info(pool)


def delete_pool(
    conn: libvirt.virConnect,
    name: str,
    force: bool = False,
) -> None:
    """Stop and undefine a storage pool.

    Raises:
        ValueError: if pool not found, is the current default, or has volumes
                    and *force* is False.
    """
    pool = libvirt_service.get_storage_pool(conn, name)

    if name == settings_service.get_default_pool():
        raise ValueError(f"Cannot delete '{name}': it is the KVMify default pool")

    try:
        vol_count = pool.numOfVolumes() if pool.isActive() else 0
    except libvirt.libvirtError:
        vol_count = 0

    if vol_count > 0 and not force:
        raise ValueError(
            f"Pool '{name}' contains {vol_count} volume(s). Use force=true to delete anyway."
        )

    try:
        if pool.isActive():
            pool.destroy()
        pool.undefine()
    except libvirt.libvirtError as exc:
        raise ValueError(str(exc)) from exc


def patch_pool(
    conn: libvirt.virConnect,
    name: str,
    body: schemas.PoolAction,
) -> schemas.PoolInfo:
    """Apply lifecycle action and/or autostart change to an existing pool.

    Raises:
        ValueError: if pool not found or action fails.
    """
    pool = libvirt_service.get_storage_pool(conn, name)

    try:
        if body.action == "start":
            pool.create(0)
        elif body.action == "stop":
            pool.destroy()
        elif body.action == "refresh":
            pool.refresh(0)

        if body.autostart is not None:
            pool.setAutostart(1 if body.autostart else 0)
    except libvirt.libvirtError as exc:
        raise ValueError(str(exc)) from exc

    return _build_pool_info(pool)


def set_default_pool(conn: libvirt.virConnect, name: str) -> str:
    """Validate the pool exists then persist it as the default.

    Returns:
        The pool name that was set as default.

    Raises:
        ValueError: if no pool with *name* exists.
    """
    libvirt_service.get_storage_pool(conn, name)  # raises ValueError if not found
    settings_service.set_default_pool(name)
    return name

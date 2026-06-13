"""Single seam for all libvirt access.

Every router/service obtains a connection via the ``connection()`` context
manager.  Tests monkeypatch ``connect`` (and/or ``connection``) to inject a
mock libvirt connection without touching a real hypervisor.
"""
from __future__ import annotations

import libvirt
from contextlib import contextmanager
from typing import Generator

from api import config


def connect() -> libvirt.virConnect:
    """Open a read-write connection to the libvirt daemon.

    Returns a ``libvirt.virConnect`` object.  The caller is responsible for
    closing it (prefer using :func:`connection` instead).

    This is the **sole function tests monkeypatch** to inject a mock
    connection::

        monkeypatch.setattr("api.services.libvirt_service.connect", lambda: mock_conn)
    """
    return libvirt.open(config.LIBVIRT_URI)


@contextmanager
def connection() -> Generator[libvirt.virConnect, None, None]:
    """Context manager that opens a libvirt connection and closes it on exit.

    Usage::

        with libvirt_service.connection() as conn:
            domains = conn.listAllDomains()
    """
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Small domain helpers
# ---------------------------------------------------------------------------

def get_domain(conn: libvirt.virConnect, name: str) -> libvirt.virDomain:
    """Return the domain named *name* or raise :class:`ValueError`.

    Raises:
        ValueError: if no domain with that name exists.
    """
    try:
        return conn.lookupByName(name)
    except libvirt.libvirtError as exc:
        raise ValueError(f"Domain '{name}' not found: {exc}") from exc


def get_storage_pool(conn: libvirt.virConnect, name: str) -> libvirt.virStoragePool:
    """Return the storage pool named *name* or raise :class:`ValueError`.

    Raises:
        ValueError: if no pool with that name exists.
    """
    try:
        return conn.storagePoolLookupByName(name)
    except libvirt.libvirtError as exc:
        raise ValueError(f"Storage pool '{name}' not found: {exc}") from exc

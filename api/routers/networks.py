"""Networks router — GET /networks.

Returns the list of libvirt networks plus a synthetic Macvtap option.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import libvirt
from fastapi import APIRouter, HTTPException

from api import schemas
from api.services import libvirt_service

router = APIRouter()


def _parse_network(net: libvirt.virNetwork) -> schemas.NetworkOption | None:
    """Parse a libvirt network XML descriptor into a :class:`NetworkOption`.

    Returns ``None`` for network types we do not surface (e.g. a second bridge
    that we choose to skip; currently all are surfaced).
    """
    xml_desc = net.XMLDesc(0)
    try:
        root = ET.fromstring(xml_desc)
    except ET.ParseError:
        return None

    name = net.name()
    forward_el = root.find("forward")

    if forward_el is None:
        # Isolated / no-forward network — treat as nat-like
        mode = "nat"
        source = None
        label = f"{name} (Isolated)"
        return schemas.NetworkOption(id=name, label=label, mode=mode, source=source)

    forward_mode = forward_el.attrib.get("mode", "nat")

    if forward_mode == "bridge":
        # Host bridge forwarding — get the bridge name from <bridge name=...>
        bridge_el = root.find("bridge")
        bridge_name = bridge_el.attrib.get("name", "") if bridge_el is not None else ""
        source = bridge_name or None
        label = f"{name} (Bridge → {bridge_name})" if bridge_name else f"{name} (Bridge)"
        return schemas.NetworkOption(
            id=name,
            label=label,
            mode="bridge",
            source=source,
            is_default=False,  # marked below for the first bridge net
        )

    if forward_mode in ("nat", "route", "open"):
        label = f"{name} (NAT)"
        return schemas.NetworkOption(id=name, label=label, mode="nat", source=None)

    # Other modes (passthrough, private, hostdev) — surface as nat for now
    label = f"{name} ({forward_mode})"
    return schemas.NetworkOption(id=name, label=label, mode="nat", source=None)


@router.get("", response_model=list[schemas.NetworkOption])
def list_networks() -> list[schemas.NetworkOption]:
    """List all available network options.

    Enumerates active and inactive libvirt networks, maps each to a
    :class:`~api.schemas.NetworkOption`, and appends a synthetic *macvtap*
    entry.  The first bridge network found is marked ``is_default=True``.
    """
    try:
        with libvirt_service.connection() as conn:
            nets = conn.listAllNetworks(0)
    except libvirt.libvirtError as exc:
        raise HTTPException(status_code=503, detail=f"libvirt unavailable: {exc}")

    options: list[schemas.NetworkOption] = []
    first_bridge_seen = False

    for net in nets:
        opt = _parse_network(net)
        if opt is None:
            continue
        if opt.mode == "bridge" and not first_bridge_seen:
            opt.is_default = True
            first_bridge_seen = True
        options.append(opt)

    # Synthetic macvtap option — source resolved best-effort to "auto"
    options.append(
        schemas.NetworkOption(
            id="macvtap",
            label="Macvtap (LAN)",
            mode="direct",
            source="auto",
            is_default=False,
        )
    )

    return options

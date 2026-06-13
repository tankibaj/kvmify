"""Network resolution and domain network update helpers.

Translates the user-facing network ID (from ProvisionRequest / NetworkUpdateRequest)
into virt-install --network values and handles updating a domain's persistent
network interface XML.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import libvirt

from api import config


# ---------------------------------------------------------------------------
# Network arg resolution
# ---------------------------------------------------------------------------

def resolve_virtinstall_network(
    conn: libvirt.virConnect,
    network_id: str,
) -> str:
    """Convert a network_id to a virt-install --network argument value.

    Rules:
    - ``"macvtap"``  → ``"type=direct,source=<PHYSICAL_NIC>,source_mode=bridge"``
    - anything else  → ``"network=<network_id>"``

    The conn parameter is accepted for future use (e.g. validating the net
    exists) but is not currently used for the simple mapping.
    """
    if network_id == "macvtap":
        return f"type=direct,source={config.PHYSICAL_NIC},source_mode=bridge"
    return f"network={network_id}"


# ---------------------------------------------------------------------------
# Domain network update (persistent config only)
# ---------------------------------------------------------------------------

def update_domain_network(
    conn: libvirt.virConnect,
    domain: libvirt.virDomain,
    new_network_id: str,
) -> None:
    """Update the persistent domain XML to use a different network.

    Detaches the current interface from the persistent config and attaches a
    new one.  The change takes effect after the VM is next started/restarted;
    this function does NOT hot-plug on a running VM.

    Uses VIR_DOMAIN_AFFECT_CONFIG so the live domain is not disrupted.

    Args:
        conn: Open libvirt connection (used for lookupByName).
        domain: The domain to update.
        new_network_id: Target network ID (libvirt name or ``"macvtap"``).

    Raises:
        libvirt.libvirtError: if detach or attach fails.
    """
    xml_desc = domain.XMLDesc(0)
    root = ET.fromstring(xml_desc)

    # Find the first interface element
    iface_el = root.find("./devices/interface")
    if iface_el is None:
        raise ValueError("Domain has no network interface to update")

    old_iface_xml = ET.tostring(iface_el, encoding="unicode")

    # Detach old interface from persistent config
    domain.detachDeviceFlags(
        old_iface_xml,
        libvirt.VIR_DOMAIN_AFFECT_CONFIG,
    )

    # Build new interface XML
    if new_network_id == "macvtap":
        new_iface_xml = (
            f"<interface type='direct'>"
            f"<source dev='{config.PHYSICAL_NIC}' mode='bridge'/>"
            f"<model type='virtio'/>"
            f"</interface>"
        )
    else:
        new_iface_xml = (
            f"<interface type='network'>"
            f"<source network='{new_network_id}'/>"
            f"<model type='virtio'/>"
            f"</interface>"
        )

    domain.attachDeviceFlags(
        new_iface_xml,
        libvirt.VIR_DOMAIN_AFFECT_CONFIG,
    )

"""Cloud-init user-data and network-config rendering + seed file management.

Renders Jinja2 templates and writes the resulting YAML files to SEED_DIR
so provision-vm.sh can pass them to cloud-localds.
"""
from __future__ import annotations

import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from api import config

# Template directory sits alongside api/services/ → api/templates/
_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape([]),  # plain YAML, no HTML escaping
        keep_trailing_newline=True,
    )


# ---------------------------------------------------------------------------
# mask_to_prefix
# ---------------------------------------------------------------------------

def mask_to_prefix(mask: str) -> int:
    """Convert a dotted-decimal subnet mask to a CIDR prefix length.

    Examples::

        mask_to_prefix("255.255.255.0")  # → 24
        mask_to_prefix("255.255.0.0")    # → 16

    Raises:
        ValueError: if the mask is not a valid dotted-decimal subnet mask.
    """
    parts = mask.split(".")
    if len(parts) != 4:
        raise ValueError(f"Invalid subnet mask: {mask!r}")
    try:
        octets = [int(p) for p in parts]
    except ValueError:
        raise ValueError(f"Invalid subnet mask: {mask!r}")
    for octet in octets:
        if octet < 0 or octet > 255:
            raise ValueError(f"Invalid subnet mask: {mask!r}")

    # Convert to 32-bit integer and count set bits
    binary = 0
    for octet in octets:
        binary = (binary << 8) | octet

    # Validate contiguous mask (no 0-bit followed by 1-bit)
    # After the leading 1s, remaining bits must all be 0
    found_zero = False
    prefix = 0
    for bit in range(31, -1, -1):
        if binary & (1 << bit):
            if found_zero:
                raise ValueError(f"Non-contiguous subnet mask: {mask!r}")
            prefix += 1
        else:
            found_zero = True

    return prefix


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_user_data(vm_name: str, ssh_public_key: str) -> str:
    """Render cloud-init user-data YAML from the Jinja2 template."""
    env = _jinja_env()
    tmpl = env.get_template("user-data.yaml.j2")
    return tmpl.render(vm_name=vm_name, ssh_public_key=ssh_public_key)


def render_network_config(
    static_ip: str,
    prefix_length: int,
    gateway: str,
    dns: str,
) -> str:
    """Render cloud-init network-config v2 YAML from the Jinja2 template."""
    env = _jinja_env()
    tmpl = env.get_template("network-config.yaml.j2")
    return tmpl.render(
        static_ip=static_ip,
        prefix_length=prefix_length,
        gateway=gateway,
        dns=dns,
    )


# ---------------------------------------------------------------------------
# Seed file writer
# ---------------------------------------------------------------------------

def write_seed_inputs(
    vm_name: str,
    user_data: str,
    network_config: str | None,
) -> tuple[str, str | None]:
    """Write seed input files to SEED_DIR.

    Creates SEED_DIR if it does not exist.

    Returns:
        (userdata_path, networkconfig_path) — networkconfig_path is None
        when network_config is None.
    """
    os.makedirs(config.SEED_DIR, exist_ok=True)

    userdata_path = os.path.join(config.SEED_DIR, f"{vm_name}-user-data.yaml")
    with open(userdata_path, "w", encoding="utf-8") as fh:
        fh.write(user_data)

    networkconfig_path: str | None = None
    if network_config is not None:
        networkconfig_path = os.path.join(
            config.SEED_DIR, f"{vm_name}-network-config.yaml"
        )
        with open(networkconfig_path, "w", encoding="utf-8") as fh:
            fh.write(network_config)

    return userdata_path, networkconfig_path

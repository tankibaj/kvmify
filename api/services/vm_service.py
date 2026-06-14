"""VM business logic: list, detail, provision, lifecycle, resize, network update.

All libvirt interactions live here.  The router is thin: it calls these
functions and maps exceptions to HTTPException.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from typing import Optional

import psutil

import libvirt

from api import config, schemas
from api.services import (
    cloudinit_service,
    libvirt_service,
    network_service,
    pool_service,
    settings_service,
)

# ---------------------------------------------------------------------------
# libvirt domain state mapping
# ---------------------------------------------------------------------------

_STATE_MAP: dict[int, str] = {
    libvirt.VIR_DOMAIN_NOSTATE: "nostate",
    libvirt.VIR_DOMAIN_RUNNING: "running",
    libvirt.VIR_DOMAIN_BLOCKED: "blocked",
    libvirt.VIR_DOMAIN_PAUSED: "paused",
    libvirt.VIR_DOMAIN_SHUTDOWN: "shutoff",
    libvirt.VIR_DOMAIN_SHUTOFF: "shutoff",
    libvirt.VIR_DOMAIN_CRASHED: "crashed",
    libvirt.VIR_DOMAIN_PMSUSPENDED: "suspended",
}


def _state_str(domain: libvirt.virDomain) -> str:
    state, _ = domain.state(0)
    return _STATE_MAP.get(state, "unknown")


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------

def _network_from_xml(xml_desc: str) -> Optional[str]:
    """Extract the first interface's network/source from domain XML."""
    try:
        root = ET.fromstring(xml_desc)
        iface = root.find("./devices/interface")
        if iface is None:
            return None
        iface_type = iface.get("type", "")
        if iface_type == "network":
            src = iface.find("source")
            return src.get("network") if src is not None else None
        if iface_type == "direct":
            src = iface.find("source")
            return "macvtap" if src is not None else None
        return iface_type
    except ET.ParseError:
        return None


def _vnc_port_from_xml(xml_desc: str) -> Optional[int]:
    """Extract the VNC port from domain XML graphics element."""
    try:
        root = ET.fromstring(xml_desc)
        for graphics in root.findall("./devices/graphics"):
            if graphics.get("type") == "vnc":
                port = graphics.get("port")
                if port and port != "-1":
                    return int(port)
    except (ET.ParseError, ValueError):
        pass
    return None


def _first_disk_target(xml_desc: str) -> Optional[str]:
    """Return the target device name of the first virtio disk (e.g. 'vda')."""
    try:
        root = ET.fromstring(xml_desc)
        for disk in root.findall("./devices/disk"):
            if disk.get("device") == "disk":
                target = disk.find("target")
                if target is not None:
                    return target.get("dev")
    except ET.ParseError:
        pass
    return None


def _first_disk_source_path(xml_desc: str, conn: libvirt.virConnect) -> Optional[str]:
    """Resolve the source path of the first non-cdrom disk (file/block/volume)."""
    try:
        root = ET.fromstring(xml_desc)
    except ET.ParseError:
        return None
    for disk in root.findall("./devices/disk"):
        if disk.get("device") == "cdrom":
            continue
        source = disk.find("source")
        if source is None:
            continue
        dtype = disk.get("type")
        if dtype == "file" and source.get("file"):
            return source.get("file")
        if dtype == "block" and source.get("dev"):
            return source.get("dev")
        if dtype == "volume" and source.get("pool") and source.get("volume"):
            try:
                pool = conn.storagePoolLookupByName(source.get("pool"))
                return pool.storageVolLookupByName(source.get("volume")).path()
            except libvirt.libvirtError:
                return None
    return None


def _disk_gb_from_xml(xml_desc: str) -> Optional[int]:
    """Extract disk capacity in GB from the first disk element (best-effort)."""
    # We can't get actual capacity from XML alone without a pool vol lookup;
    # return None and let the router omit it or fetch via pool vol.
    return None


def _vcpus_from_xml(xml_desc: str) -> Optional[int]:
    """Read the configured (maximum) vCPU count from domain XML.

    Parsing the XML works for BOTH running and stopped domains.  ``maxVcpus()``
    (virDomainGetMaxVcpus) raises "domain is not running" for inactive domains,
    so it must not be used in the detail path — stopped VMs are valid.
    """
    try:
        root = ET.fromstring(xml_desc)
        vcpu_el = root.find("vcpu")
        if vcpu_el is not None and vcpu_el.text and vcpu_el.text.strip().isdigit():
            return int(vcpu_el.text.strip())
    except ET.ParseError:
        pass
    return None


def _best_ip(domain: libvirt.virDomain) -> Optional[str]:
    """Best-effort IPv4 extraction across multiple libvirt sources.

    NAT networks expose a DHCP lease (LEASE); bridge/macvtap VMs are leased by
    the LAN router, not libvirt, so their address is only discoverable from the
    host ARP table (ARP, once the VM has sent traffic) or the guest agent
    (AGENT, if installed). Try each in turn.
    """
    sources = (
        libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE,
        libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_ARP,
        libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT,
    )
    for source in sources:
        try:
            ifaces = domain.interfaceAddresses(source, 0)
        except (libvirt.libvirtError, Exception):
            continue
        for _iface, data in (ifaces or {}).items():
            for addr in data.get("addrs", []):
                ip = addr.get("addr", "")
                if addr.get("type") == libvirt.VIR_IP_ADDR_TYPE_IPV4 and not ip.startswith(
                    "127."
                ):
                    return ip
    return None


# ---------------------------------------------------------------------------
# list_vms
# ---------------------------------------------------------------------------

def list_vms(conn: libvirt.virConnect) -> list[schemas.VMSummary]:
    """Return summary info for all domains."""
    domains = conn.listAllDomains(0)
    result: list[schemas.VMSummary] = []
    for domain in domains:
        xml_desc = domain.XMLDesc(0)
        result.append(
            schemas.VMSummary(
                name=domain.name(),
                state=_state_str(domain),
                vcpus=_vcpus_from_xml(xml_desc),
                ram_mb=domain.maxMemory() // 1024,
                ip=_best_ip(domain),
                network=_network_from_xml(xml_desc),
            )
        )
    return result


# ---------------------------------------------------------------------------
# get_vm
# ---------------------------------------------------------------------------

def get_vm(conn: libvirt.virConnect, name: str) -> schemas.VMDetail:
    """Return full detail for a single domain.

    Raises:
        ValueError: if the domain does not exist.
    """
    domain = libvirt_service.get_domain(conn, name)
    xml_desc = domain.XMLDesc(0)

    # CPU percent (best-effort single sample — not a proper interval average)
    cpu_percent: Optional[float] = None
    try:
        stats = domain.getCPUStats(True, 0)
        # stats[0] is total CPU stats; cpu_time is in nanoseconds
        # A single sample gives raw ns, not a meaningful %; return None for now.
        # Callers wanting a real % should use /stats endpoint.
        cpu_percent = None
    except (libvirt.libvirtError, Exception):
        cpu_percent = None

    # RAM used
    ram_used_mb: Optional[int] = None
    try:
        mem_stats = domain.memoryStats()
        # available = total balloon target in KB; rss = resident set
        if "rss" in mem_stats:
            ram_used_mb = mem_stats["rss"] // 1024
        elif "actual" in mem_stats and "unused" in mem_stats:
            ram_used_mb = (mem_stats["actual"] - mem_stats["unused"]) // 1024
    except (libvirt.libvirtError, Exception):
        ram_used_mb = None

    return schemas.VMDetail(
        name=domain.name(),
        state=_state_str(domain),
        vcpus=_vcpus_from_xml(xml_desc),
        ram_mb=domain.maxMemory() // 1024,
        ip=_best_ip(domain),
        network=_network_from_xml(xml_desc),
        cpu_percent=cpu_percent,
        ram_used_mb=ram_used_mb,
        ram_total_mb=domain.maxMemory() // 1024,
        disk_gb=_disk_gb_from_xml(xml_desc),
        vnc_port=_vnc_port_from_xml(xml_desc),
    )


# ---------------------------------------------------------------------------
# provision
# ---------------------------------------------------------------------------

def provision(
    conn: libvirt.virConnect,
    req: schemas.ProvisionRequest,
) -> schemas.ProvisionResult:
    """Provision a new VM from a base image.

    Steps:
    1. Validate (name uniqueness, base image exists, pool space).
    2. Render and write cloud-init seed inputs.
    3. Resolve network arg for virt-install.
    4. Run provision-vm.sh via subprocess (sudo).
    5. Refresh pool and poll for IP.
    6. Return ProvisionResult.

    Raises:
        ValueError: on validation failures or script errors.
    """
    vm_name = req.vm_name

    # 1a. Name uniqueness
    try:
        conn.lookupByName(vm_name)
        raise ValueError(f"VM '{vm_name}' already exists")
    except libvirt.libvirtError:
        pass  # expected — domain not found

    # 1b. Base image / template path
    if req.source_type == "template" and req.template_name:
        base_img_path = os.path.join(config.TEMPLATES_DIR, f"{req.template_name}.qcow2")
        if not os.path.exists(base_img_path):
            raise ValueError(f"Template '{req.template_name}' not found at {base_img_path}")
    else:
        base_img_name = config.BASE_IMAGE_NAMES[req.ubuntu_version]
        base_img_path = os.path.join(config.BASE_IMAGE_DIR, base_img_name)
        if not os.path.exists(base_img_path):
            raise ValueError(
                f"Base image not found: {base_img_path}. "
                f"Run POST /images/sync to download it first."
            )

    # 1c. Resolve storage pool + disk path
    pool_name = req.storage_pool or settings_service.get_default_pool()
    try:
        pool = conn.storagePoolLookupByName(pool_name)
    except libvirt.libvirtError:
        pool = None

    if pool is not None and pool.isActive():
        pool_info = pool.info()
        available_gb = pool_info[3] // (1024 ** 3)
        if available_gb < req.disk_gb:
            raise ValueError(
                f"Pool '{pool_name}' has only {available_gb} GB free; "
                f"requested {req.disk_gb} GB"
            )
        pool_path = pool_service._pool_path_from_xml(pool.XMLDesc(0))
    else:
        pool_path = config.VM_DISK_DIR

    disk_path = os.path.join(pool_path, f"{vm_name}.qcow2")

    # 1d. Validate subnet mask if static
    prefix_length: Optional[int] = None
    if req.ip_mode == "static":
        if not req.subnet_mask:
            raise ValueError("subnet_mask is required for static IP mode")
        prefix_length = cloudinit_service.mask_to_prefix(req.subnet_mask)

    # 2. Render and write cloud-init seed inputs
    user_data = cloudinit_service.render_user_data(vm_name, req.ssh_public_key)

    network_config_content: Optional[str] = None
    if req.ip_mode == "static":
        network_config_content = cloudinit_service.render_network_config(
            static_ip=req.static_ip,  # type: ignore[arg-type]
            prefix_length=prefix_length,  # type: ignore[arg-type]
            gateway=req.gateway,  # type: ignore[arg-type]
            dns=req.dns or "8.8.8.8",
        )

    userdata_path, networkconfig_path = cloudinit_service.write_seed_inputs(
        vm_name, user_data, network_config_content
    )

    # 3. Resolve network arg
    network_arg = network_service.resolve_virtinstall_network(conn, req.network)

    # 4. OS variant
    if req.source_type == "template" and req.template_name:
        _tpl_json = os.path.join(config.TEMPLATES_DIR, f"{req.template_name}.json")
        os_variant = "ubuntu22.04"  # safe default
        try:
            import json as _json
            with open(_tpl_json) as _fh:
                _meta = _json.load(_fh)
            os_variant = _meta.get("os_variant") or "ubuntu22.04"
        except (FileNotFoundError, KeyError, ValueError, OSError):
            pass
    else:
        os_variant = config.OS_VARIANTS[req.ubuntu_version]

    # 5. Build subprocess command
    cmd = [
        "sudo",
        config.PROVISION_SCRIPT,
        vm_name,
        base_img_path,
        disk_path,
        str(req.disk_gb),
        str(req.cpu),
        str(req.ram_mb),
        network_arg,
        os_variant,
        userdata_path,
    ]
    if networkconfig_path:
        cmd.append(networkconfig_path)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            f"Provision script failed (exit {exc.returncode}):\n"
            f"{exc.stderr or exc.stdout}"
        ) from exc

    # 6. Refresh pool so libvirt sees the new volumes
    if pool is not None and pool.isActive():
        try:
            pool.refresh(0)
        except libvirt.libvirtError:
            pass

    # 7. Poll for domain + IP (up to 120 s)
    ip: Optional[str] = None
    vnc_port: Optional[int] = None
    deadline = time.time() + 120
    domain = None
    while time.time() < deadline:
        try:
            domain = conn.lookupByName(vm_name)
            break
        except libvirt.libvirtError:
            time.sleep(3)

    if domain is not None:
        vnc_port = _vnc_port_from_xml(domain.XMLDesc(0))
        # Poll for IP
        while time.time() < deadline:
            ip = _best_ip(domain)
            if ip:
                break
            time.sleep(3)

    return schemas.ProvisionResult(
        vm_name=vm_name,
        status="provisioned",
        ip=ip,
        vnc_port=vnc_port,
        network=req.network,
        ip_mode=req.ip_mode,
        message=result.stdout.strip() if result.stdout else None,
    )


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

def start_vm(conn: libvirt.virConnect, name: str) -> None:
    """Start a stopped VM.

    Raises:
        ValueError: if domain not found or libvirt call fails.
    """
    domain = libvirt_service.get_domain(conn, name)
    try:
        domain.create()
    except libvirt.libvirtError as exc:
        raise ValueError(str(exc)) from exc


def stop_vm(conn: libvirt.virConnect, name: str) -> None:
    """Gracefully shut down a VM via ACPI.

    Raises:
        ValueError: if domain not found or libvirt call fails.
    """
    domain = libvirt_service.get_domain(conn, name)
    try:
        domain.shutdown()
    except libvirt.libvirtError as exc:
        raise ValueError(str(exc)) from exc


def restart_vm(conn: libvirt.virConnect, name: str) -> None:
    """Reboot a running VM.

    Raises:
        ValueError: if domain not found or libvirt call fails.
    """
    domain = libvirt_service.get_domain(conn, name)
    try:
        domain.reboot(0)
    except libvirt.libvirtError as exc:
        raise ValueError(str(exc)) from exc


def delete_vm(conn: libvirt.virConnect, name: str) -> None:
    """Destroy (if running) then undefine a VM and delete its disk volumes.

    Raises:
        ValueError: if domain not found.
    """
    domain = libvirt_service.get_domain(conn, name)

    # Destroy if running
    try:
        state, _ = domain.state(0)
        if state == libvirt.VIR_DOMAIN_RUNNING:
            domain.destroy()
    except libvirt.libvirtError:
        pass

    # Collect volume paths before undefining
    xml_desc = domain.XMLDesc(0)
    disk_paths: list[str] = []
    try:
        root = ET.fromstring(xml_desc)
        for disk in root.findall("./devices/disk"):
            source = disk.find("source")
            if source is not None:
                path = source.get("file") or source.get("dev") or source.get("volume")
                if path:
                    disk_paths.append(path)
    except ET.ParseError:
        pass

    # Undefine the domain
    try:
        flags = 0
        try:
            flags = (
                libvirt.VIR_DOMAIN_UNDEFINE_MANAGED_SAVE
                | libvirt.VIR_DOMAIN_UNDEFINE_SNAPSHOTS_METADATA
            )
        except AttributeError:
            flags = 0
        domain.undefineFlags(flags)
    except libvirt.libvirtError:
        try:
            domain.undefine()
        except libvirt.libvirtError as exc:
            raise ValueError(str(exc)) from exc

    # Delete volumes
    for vol_path in disk_paths:
        try:
            vol = conn.storageVolLookupByPath(vol_path)
            vol.delete(0)
        except (libvirt.libvirtError, Exception):
            pass  # best-effort; volume may already be gone

    # Remove any stale noVNC console token for this VM
    try:
        os.remove(os.path.join(config.NOVNC_TOKEN_DIR, name))
    except OSError:
        pass  # no token registered / already gone


# ---------------------------------------------------------------------------
# Resize
# ---------------------------------------------------------------------------

def resize_vm(
    conn: libvirt.virConnect,
    name: str,
    req: schemas.ResizeRequest,
) -> dict:
    """Resize vCPUs, RAM, and/or disk for a domain.

    - CPU and RAM changes require the VM to be stopped.
    - Disk resize can be done online.

    Raises:
        ValueError: if VM not found, or VM is running when CPU/RAM resize requested.
    """
    domain = libvirt_service.get_domain(conn, name)
    state, _ = domain.state(0)
    is_running = state == libvirt.VIR_DOMAIN_RUNNING

    if (req.cpu is not None or req.ram_mb is not None) and is_running:
        raise ValueError(
            "CPU and RAM resize require the VM to be stopped first"
        )

    changes: list[str] = []

    if req.cpu is not None:
        try:
            # Raise the configured MAXIMUM first, then the current count —
            # otherwise growing beyond the VM's original max vCPUs is rejected
            # ("requested vcpus is greater than max allowable vcpus").
            domain.setVcpusFlags(
                req.cpu,
                libvirt.VIR_DOMAIN_AFFECT_CONFIG | libvirt.VIR_DOMAIN_VCPU_MAXIMUM,
            )
            domain.setVcpusFlags(
                req.cpu,
                libvirt.VIR_DOMAIN_AFFECT_CONFIG,
            )
            changes.append(f"cpu={req.cpu}")
        except libvirt.libvirtError as exc:
            raise ValueError(f"Failed to set vCPUs: {exc}") from exc

    if req.ram_mb is not None:
        mem_kb = req.ram_mb * 1024
        try:
            domain.setMemoryFlags(
                mem_kb,
                libvirt.VIR_DOMAIN_AFFECT_CONFIG | libvirt.VIR_DOMAIN_MEM_MAXIMUM,
            )
            domain.setMemoryFlags(
                mem_kb,
                libvirt.VIR_DOMAIN_AFFECT_CONFIG,
            )
            changes.append(f"ram_mb={req.ram_mb}")
        except libvirt.libvirtError as exc:
            raise ValueError(f"Failed to set memory: {exc}") from exc

    if req.disk_gb is not None:
        xml_desc = domain.XMLDesc(0)
        new_bytes = req.disk_gb * 1024 ** 3

        # Determine current disk capacity from the backing storage volume.
        path = _first_disk_source_path(xml_desc, conn)
        vol = None
        cur_bytes = None
        if path is not None:
            try:
                vol = conn.storageVolLookupByPath(path)
                cur_bytes = vol.info()[1]  # [type, capacity, allocation]
            except libvirt.libvirtError:
                vol = None

        if cur_bytes is not None and new_bytes == cur_bytes:
            pass  # no change requested — skip (blockResize would fail on a stopped VM)
        elif cur_bytes is not None and new_bytes < cur_bytes:
            raise ValueError(
                f"Disk can only be grown; current size is "
                f"{cur_bytes // 1024 ** 3} GB"
            )
        else:
            # Grow: online (blockResize, guest sees it live) when running,
            # offline (volume resize) when the VM is stopped.
            try:
                if is_running:
                    target_dev = _first_disk_target(xml_desc)
                    if target_dev is None:
                        raise ValueError("No disk target device found in domain XML")
                    domain.blockResize(
                        target_dev, new_bytes, libvirt.VIR_DOMAIN_BLOCK_RESIZE_BYTES
                    )
                elif vol is not None:
                    vol.resize(new_bytes)
                else:
                    raise ValueError("Cannot resize disk: backing volume not found")
                changes.append(f"disk_gb={req.disk_gb}")
            except libvirt.libvirtError as exc:
                raise ValueError(f"Failed to resize disk: {exc}") from exc

    return {"message": f"Resize applied: {', '.join(changes) or 'no changes'}"}


# ---------------------------------------------------------------------------
# Network update
# ---------------------------------------------------------------------------

def update_network(
    conn: libvirt.virConnect,
    name: str,
    req: schemas.NetworkUpdateRequest,
) -> dict:
    """Update the persistent network config of a domain.

    Changes take effect after the VM is restarted.

    Raises:
        ValueError: if domain not found or update fails.
    """
    domain = libvirt_service.get_domain(conn, name)
    try:
        network_service.update_domain_network(conn, domain, req.network)
    except (libvirt.libvirtError, ValueError) as exc:
        raise ValueError(str(exc)) from exc

    return {
        "message": "Network updated. Restart VM for changes to take effect.",
        "network": req.network,
        "ip_mode": req.ip_mode,
    }


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------

def _sleep(seconds: float) -> None:
    """Thin wrapper around time.sleep — monkeypatched in tests."""
    time.sleep(seconds)


def sample_cpu_percent(
    conn: libvirt.virConnect,
    name: str,
    interval: float = 0.5,
) -> Optional[float]:
    """Return a two-sample CPU utilisation percentage for a domain.

    Reads cpu_time (nanoseconds, field index 4 of domain.info()) twice,
    separated by *interval* seconds, then computes:

        delta_cpu_ns / (interval * 1e9 * host_cpu_count) * 100

    Clamped to [0, 100].  Returns None on any error.
    """
    domain = libvirt_service.get_domain(conn, name)
    try:
        host_cpu_count: int = conn.getInfo()[2]
        if host_cpu_count < 1:
            host_cpu_count = 1

        info1 = domain.info()
        cpu_time1: int = info1[4]

        _sleep(interval)

        info2 = domain.info()
        cpu_time2: int = info2[4]

        delta_ns = cpu_time2 - cpu_time1
        cpu_pct = (delta_ns / (interval * 1e9 * host_cpu_count)) * 100.0
        return round(max(0.0, min(100.0, cpu_pct)), 1)
    except (libvirt.libvirtError, Exception):
        return None


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def get_stats(conn: libvirt.virConnect, name: str) -> dict:
    """Return a single-sample CPU% and RAM% for a running VM.

    Raises:
        ValueError: if domain not found.
    """
    domain = libvirt_service.get_domain(conn, name)

    cpu_percent: Optional[float] = None
    ram_percent: Optional[float] = None

    try:
        stats = domain.getCPUStats(True, 0)
        # Single sample: we can't compute a delta; return None
        cpu_percent = None
    except (libvirt.libvirtError, Exception):
        cpu_percent = None

    try:
        mem_stats = domain.memoryStats()
        total = domain.maxMemory()  # KB
        if total and "unused" in mem_stats and "actual" in mem_stats:
            used = mem_stats["actual"] - mem_stats["unused"]
            ram_percent = round((used / total) * 100, 1)
    except (libvirt.libvirtError, Exception):
        ram_percent = None

    return {"cpu_percent": cpu_percent, "ram_percent": ram_percent}


# ---------------------------------------------------------------------------
# Console port
# ---------------------------------------------------------------------------

def console_port(conn: libvirt.virConnect, name: str) -> int:
    """Return the VNC port for a domain.

    Raises:
        ValueError: if domain not found or has no VNC graphics.
    """
    domain = libvirt_service.get_domain(conn, name)
    xml_desc = domain.XMLDesc(0)
    port = _vnc_port_from_xml(xml_desc)
    if port is None:
        raise ValueError(f"VM '{name}' has no VNC graphics configured")
    return port


def register_console_token(conn: libvirt.virConnect, name: str) -> dict:
    """Resolve the VM's VNC port and register a websockify token for it.

    Writes ``<NOVNC_TOKEN_DIR>/<name>`` containing ``<name>: 127.0.0.1:<port>``
    so the shared websockify proxy can route ``?token=<name>`` to this VM.

    Returns ``{vnc_port, token, path}`` for the frontend noVNC client.
    """
    port = console_port(conn, name)
    os.makedirs(config.NOVNC_TOKEN_DIR, exist_ok=True)
    token_path = os.path.join(config.NOVNC_TOKEN_DIR, name)
    with open(token_path, "w") as fh:
        fh.write(f"{name}: 127.0.0.1:{port}\n")
    return {"vnc_port": port, "token": name, "path": "websockify"}

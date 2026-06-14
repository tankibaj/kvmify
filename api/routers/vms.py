"""VMs router — thin HTTP layer delegating to vm_service."""
from __future__ import annotations

import libvirt
from fastapi import APIRouter, HTTPException

from api import schemas
from api.services import libvirt_service, vm_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Error mapping helper
# ---------------------------------------------------------------------------

def _map_error(exc: ValueError) -> HTTPException:
    """Map a service-layer ValueError to an appropriate HTTPException.

    404 → domain/VM not found (libvirt resource missing)
    409 → name conflict or illegal state
    400 → everything else (bad input, missing file, validation failure)
    """
    msg = str(exc)
    lower = msg.lower()
    # 404 only for VM domain not found — not for missing base image files, etc.
    if "domain '" in lower and "not found" in lower:
        return HTTPException(status_code=404, detail=msg)
    if "not found" in lower and "domain" in lower:
        return HTTPException(status_code=404, detail=msg)
    if "already exists" in lower:
        return HTTPException(status_code=409, detail=msg)
    return HTTPException(status_code=400, detail=msg)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=list[schemas.VMSummary])
def list_vms() -> list[schemas.VMSummary]:
    """List all VMs with summary info."""
    try:
        with libvirt_service.connection() as conn:
            return vm_service.list_vms(conn)
    except ValueError as exc:
        raise _map_error(exc)


@router.post("/provision", response_model=schemas.ProvisionResult, status_code=201)
def provision(req: schemas.ProvisionRequest) -> schemas.ProvisionResult:
    """Provision a new VM from a cloud base image."""
    try:
        with libvirt_service.connection() as conn:
            return vm_service.provision(conn, req)
    except ValueError as exc:
        raise _map_error(exc)


@router.get("/{name}", response_model=schemas.VMDetail)
def get_vm(name: str) -> schemas.VMDetail:
    """Get full detail for a single VM."""
    try:
        with libvirt_service.connection() as conn:
            return vm_service.get_vm(conn, name)
    except ValueError as exc:
        raise _map_error(exc)


@router.post("/{name}/start")
def start_vm(name: str) -> dict:
    """Start a stopped VM."""
    try:
        with libvirt_service.connection() as conn:
            vm_service.start_vm(conn, name)
    except ValueError as exc:
        raise _map_error(exc)
    return {"message": f"VM '{name}' start initiated"}


@router.post("/{name}/stop")
def stop_vm(name: str) -> dict:
    """Gracefully shut down a VM via ACPI."""
    try:
        with libvirt_service.connection() as conn:
            vm_service.stop_vm(conn, name)
    except ValueError as exc:
        raise _map_error(exc)
    return {"message": f"VM '{name}' shutdown initiated"}


@router.post("/{name}/restart")
def restart_vm(name: str) -> dict:
    """Reboot a running VM."""
    try:
        with libvirt_service.connection() as conn:
            vm_service.restart_vm(conn, name)
    except ValueError as exc:
        raise _map_error(exc)
    return {"message": f"VM '{name}' reboot initiated"}


@router.delete("/{name}", status_code=204)
def delete_vm(name: str) -> None:
    """Delete a VM: destroy (if running), undefine, and remove disk volumes."""
    try:
        with libvirt_service.connection() as conn:
            vm_service.delete_vm(conn, name)
    except ValueError as exc:
        raise _map_error(exc)


@router.patch("/{name}/resize")
def resize_vm(name: str, req: schemas.ResizeRequest) -> dict:
    """Resize vCPUs, RAM, and/or disk for a VM."""
    try:
        with libvirt_service.connection() as conn:
            return vm_service.resize_vm(conn, name, req)
    except ValueError as exc:
        msg = str(exc)
        if "stopped" in msg.lower() or "require" in msg.lower():
            raise HTTPException(status_code=409, detail=msg)
        raise _map_error(exc)


@router.patch("/{name}/network")
def update_network(name: str, req: schemas.NetworkUpdateRequest) -> dict:
    """Update the network config for a VM (takes effect after restart)."""
    try:
        with libvirt_service.connection() as conn:
            return vm_service.update_network(conn, name, req)
    except ValueError as exc:
        raise _map_error(exc)


@router.get("/{name}/console")
def console(name: str) -> dict:
    """Register a websockify token for the VM and return console connect info."""
    try:
        with libvirt_service.connection() as conn:
            return vm_service.register_console_token(conn, name)
    except ValueError as exc:
        raise _map_error(exc)


@router.get("/{name}/stats", response_model=schemas.VMStats)
def vm_stats(name: str) -> schemas.VMStats:
    """Return a two-sample CPU% and RAM% for a running VM."""
    try:
        with libvirt_service.connection() as conn:
            domain = libvirt_service.get_domain(conn, name)
            cpu_percent = vm_service.sample_cpu_percent(conn, name, interval=0.5)

            ram_percent: float | None = None
            ram_used_mb: int | None = None
            try:
                info = domain.info()
                max_mem_kb: int = info[1]
                mem_kb: int = info[2]
                if max_mem_kb and max_mem_kb > 0:
                    ram_percent = round((mem_kb / max_mem_kb) * 100.0, 1)
                ram_used_mb = mem_kb // 1024
            except (libvirt.libvirtError, Exception):
                pass
    except ValueError as exc:
        raise _map_error(exc)

    return schemas.VMStats(
        cpu_percent=cpu_percent,
        ram_percent=ram_percent,
        ram_used_mb=ram_used_mb,
    )

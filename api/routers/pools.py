"""Pools router — full CRUD + lifecycle for libvirt storage pools."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api import schemas
from api.services import libvirt_service, pool_service

router = APIRouter()


def _service_error_to_http(exc: ValueError) -> HTTPException:
    """Map a service-layer ValueError to an appropriate HTTPException."""
    msg = str(exc)
    if "not found" in msg.lower():
        return HTTPException(status_code=404, detail=msg)
    if "already exists" in msg.lower():
        return HTTPException(status_code=400, detail=msg)
    if "default pool" in msg.lower() or "default" in msg.lower():
        return HTTPException(status_code=409, detail=msg)
    if "volume" in msg.lower():
        return HTTPException(status_code=409, detail=msg)
    return HTTPException(status_code=400, detail=msg)


@router.get("", response_model=list[schemas.PoolInfo])
def list_pools() -> list[schemas.PoolInfo]:
    """List all libvirt storage pools with runtime stats."""
    try:
        with libvirt_service.connection() as conn:
            return pool_service.list_pools(conn)
    except ValueError as exc:
        raise _service_error_to_http(exc)


@router.post("", response_model=schemas.PoolInfo, status_code=201)
def create_pool(body: schemas.PoolCreate) -> schemas.PoolInfo:
    """Create, build, start, and autostart a new directory-type pool."""
    try:
        with libvirt_service.connection() as conn:
            return pool_service.create_pool(conn, body)
    except ValueError as exc:
        raise _service_error_to_http(exc)


@router.delete("/{name}", status_code=204)
def delete_pool(
    name: str,
    force: bool = Query(False, description="Delete even if pool contains volumes"),
) -> None:
    """Stop and undefine a storage pool.

    - Returns 409 if the pool is the current KVMify default.
    - Returns 409 if the pool contains volumes and ``force`` is not set.
    - Returns 404 if the pool does not exist.
    """
    try:
        with libvirt_service.connection() as conn:
            pool_service.delete_pool(conn, name, force=force)
    except ValueError as exc:
        raise _service_error_to_http(exc)


@router.patch("/{name}", response_model=schemas.PoolInfo)
def patch_pool(name: str, body: schemas.PoolAction) -> schemas.PoolInfo:
    """Apply a lifecycle action and/or autostart change to a pool."""
    try:
        with libvirt_service.connection() as conn:
            return pool_service.patch_pool(conn, name, body)
    except ValueError as exc:
        raise _service_error_to_http(exc)


@router.post("/{name}/default")
def set_default_pool(name: str) -> dict[str, str]:
    """Mark a pool as the KVMify default provisioning pool."""
    try:
        with libvirt_service.connection() as conn:
            pool_name = pool_service.set_default_pool(conn, name)
    except ValueError as exc:
        raise _service_error_to_http(exc)
    return {"default_pool": pool_name}

"""Snapshots router — thin HTTP layer delegating to snapshot_service."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api import schemas
from api.services import libvirt_service, snapshot_service, template_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Error mapping helper
# ---------------------------------------------------------------------------

def _map_error(exc: Exception) -> HTTPException:
    """Map service exceptions to HTTPException.

    LookupError → 404
    ValueError with "already exists" → 409
    Other ValueError → 400
    """
    msg = str(exc)
    lower = msg.lower()
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=msg)
    if "already exists" in lower:
        return HTTPException(status_code=409, detail=msg)
    if "domain '" in lower and "not found" in lower:
        return HTTPException(status_code=404, detail=msg)
    return HTTPException(status_code=400, detail=msg)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/{name}/snapshots", response_model=list[schemas.SnapshotInfo])
def list_snapshots(name: str) -> list[schemas.SnapshotInfo]:
    """List all snapshots for a VM."""
    try:
        with libvirt_service.connection() as conn:
            items = snapshot_service.list_snapshots(conn, name)
    except (ValueError, LookupError) as exc:
        raise _map_error(exc)
    return [schemas.SnapshotInfo(**item) for item in items]


@router.post("/{name}/snapshots", response_model=schemas.SnapshotInfo, status_code=201)
def take_snapshot(name: str, req: schemas.SnapshotCreate) -> schemas.SnapshotInfo:
    """Take a new snapshot of a VM."""
    try:
        with libvirt_service.connection() as conn:
            info = snapshot_service.take_snapshot(conn, name, req.name, req.description)
    except (ValueError, LookupError) as exc:
        raise _map_error(exc)
    return schemas.SnapshotInfo(**info)


@router.post("/{name}/snapshots/{snap}/restore")
def restore_snapshot(name: str, snap: str) -> dict:
    """Restore a VM to a named snapshot."""
    try:
        with libvirt_service.connection() as conn:
            snapshot_service.restore_snapshot(conn, name, snap)
    except (ValueError, LookupError) as exc:
        raise _map_error(exc)
    return {"message": f"VM '{name}' reverted to snapshot '{snap}'"}


@router.delete("/{name}/snapshots/{snap}", status_code=204)
def delete_snapshot(name: str, snap: str) -> None:
    """Delete a snapshot from a VM."""
    try:
        with libvirt_service.connection() as conn:
            snapshot_service.delete_snapshot(conn, name, snap)
    except (ValueError, LookupError) as exc:
        raise _map_error(exc)


@router.post("/{name}/snapshots/{snap}/export", status_code=201, response_model=schemas.TemplateInfo)
def export_snapshot_as_template(name: str, snap: str, body: schemas.TemplateExportRequest) -> schemas.TemplateInfo:
    """Export a VM snapshot as a standalone reusable template."""
    try:
        with libvirt_service.connection() as conn:
            info = template_service.export_from_snapshot(conn, name, snap, body.template_name)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return schemas.TemplateInfo(**info)

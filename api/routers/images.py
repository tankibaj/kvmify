"""Images router — list base images and trigger / monitor sync."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from api import schemas
from api.services import image_service

router = APIRouter()

_VALID_VERSIONS = image_service.VALID_VERSIONS


@router.get("", response_model=list[schemas.ImageInfo])
def list_images() -> list[schemas.ImageInfo]:
    """List all Ubuntu base images with local status vs upstream."""
    return image_service.list_images()


@router.post("/sync", response_model=schemas.SyncStatus)
def sync_images(body: schemas.SyncRequest) -> schemas.SyncStatus:
    """Trigger a background sync of one or all base images.

    - ``version`` must be one of ``2004``, ``2204``, ``2404`` (or omitted to sync all).
    - Returns ``state=running`` immediately; the script runs in the background.
    - Poll ``GET /images/sync/status`` for completion.
    """
    if body.version is not None and body.version not in _VALID_VERSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid version '{body.version}'. Must be one of {sorted(_VALID_VERSIONS)}.",
        )
    status_dict = image_service.trigger_sync(body.version)
    return schemas.SyncStatus(**status_dict)


@router.get("/sync/status", response_model=schemas.SyncStatus)
def get_sync_status() -> schemas.SyncStatus:
    """Return the current (or last-known) sync status."""
    return image_service.get_sync_status()


@router.post("", status_code=201)
def add_custom_image(body: schemas.CustomImageCreate) -> dict:
    """Add a custom base image by URL. Downloads in background via download-base-image.sh."""
    try:
        return image_service.add_custom_image(body.label, body.url, body.os_variant)
    except ValueError as exc:
        msg = str(exc)
        if any(word in msg.lower() for word in ("exists", "collision", "already", "collides")):
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@router.delete("/{image_id}", status_code=204)
def delete_custom_image(image_id: str) -> None:
    """Delete a custom base image. Built-in Ubuntu images cannot be deleted."""
    if image_id in image_service.VALID_VERSIONS:
        raise HTTPException(status_code=400, detail="Cannot delete a built-in Ubuntu image")
    try:
        image_service.delete_custom_image(image_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

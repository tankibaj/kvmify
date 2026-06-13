"""Images router — list base images and trigger / monitor sync."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

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

"""Host router — thin HTTP layer delegating to host_service."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api import schemas
from api.services import host_service

router = APIRouter()


@router.get("/stats", response_model=schemas.HostStats)
def get_stats() -> schemas.HostStats:
    """Return host-level CPU, RAM, and disk utilisation percentages."""
    try:
        stats = host_service.get_host_stats()
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc))
    return schemas.HostStats(**stats)

"""Templates router — thin HTTP layer for template management."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api import schemas
from api.services import template_service

router = APIRouter()


@router.get("", response_model=list[schemas.TemplateInfo])
def list_templates() -> list[schemas.TemplateInfo]:
    """List all available VM templates."""
    items = template_service.list_templates()
    return [schemas.TemplateInfo(**item) for item in items]


@router.delete("/{name}", status_code=204)
def delete_template(name: str) -> None:
    """Delete a template by name."""
    try:
        template_service.delete_template(name)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

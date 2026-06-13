"""Pydantic v2 request/response models shared across routers."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Networks
# ---------------------------------------------------------------------------

class NetworkOption(BaseModel):
    """A single network option surfaced to the frontend."""

    id: str = Field(..., description="Unique identifier (libvirt net name or 'macvtap')")
    label: str = Field(..., description="Human-readable label shown in the dropdown")
    mode: Literal["bridge", "nat", "direct"] = Field(
        ..., description="Network mode: bridge | nat | direct (macvtap)"
    )
    source: Optional[str] = Field(
        None, description="Bridge name or physical NIC for direct mode"
    )
    is_default: bool = Field(
        False, description="True for the first bridge network (pre-selected in UI)"
    )


# ---------------------------------------------------------------------------
# Storage Pools
# ---------------------------------------------------------------------------

class PoolInfo(BaseModel):
    """Runtime information about a libvirt storage pool."""

    name: str
    state: Literal["active", "inactive"]
    type: str = Field(..., description="Pool type (e.g. 'dir', 'lvm')")
    capacity: int = Field(..., description="Total capacity in bytes")
    allocation: int = Field(..., description="Allocated bytes")
    available: int = Field(..., description="Available bytes")
    autostart: bool
    path: str = Field(..., description="Target path of the pool directory")
    is_default: bool = Field(
        False, description="True if this is the KVMify default provisioning pool"
    )
    volume_count: int = Field(..., description="Number of volumes in the pool")


class PoolCreate(BaseModel):
    """Request body for creating a new directory pool."""

    name: str = Field(..., description="Pool name (must be unique)")
    path: str = Field(..., description="Absolute path on the host for the pool directory")


class PoolAction(BaseModel):
    """Request body for PATCH /pools/{name} — lifecycle + autostart update."""

    action: Optional[Literal["start", "stop", "refresh"]] = Field(
        None, description="Lifecycle action to perform"
    )
    autostart: Optional[bool] = Field(
        None, description="Set or clear autostart flag"
    )

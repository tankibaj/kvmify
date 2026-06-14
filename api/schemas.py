"""Pydantic v2 request/response models shared across routers."""
from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


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


# ---------------------------------------------------------------------------
# Base Images
# ---------------------------------------------------------------------------

class ImageInfo(BaseModel):
    """Runtime information about a locally cached Ubuntu base image."""

    version: str = Field(..., description="Short version key: '2004', '2204', or '2404'")
    codename: str = Field(..., description="Ubuntu codename: focal, jammy, or noble")
    label: str = Field(..., description="Human-readable label, e.g. 'Ubuntu 22.04 LTS'")
    status: Literal["up_to_date", "outdated", "missing", "unknown"] = Field(
        ..., description="Sync status relative to upstream cloud image"
    )
    size: Optional[int] = Field(None, description="Local file size in bytes")
    last_updated: Optional[str] = Field(None, description="ISO-8601 mtime of local file")
    checksum: Optional[str] = Field(None, description="SHA-256 hex digest of local file")


class SyncRequest(BaseModel):
    """Request body for POST /images/sync."""

    version: Optional[str] = Field(
        None, description="Version to sync: '2004', '2204', or '2404'. Omit to sync all."
    )


class SyncStatus(BaseModel):
    """Current or last-known status of the background sync process."""

    state: str = Field(..., description="One of: idle, running, finished, failed")
    version: Optional[str] = Field(None, description="Version passed to trigger_sync")
    started_at: Optional[str] = Field(None, description="ISO-8601 timestamp when sync started")
    finished_at: Optional[str] = Field(None, description="ISO-8601 timestamp when sync finished")
    returncode: Optional[int] = Field(None, description="Exit code of the sync script")
    log: Optional[str] = Field(None, description="Captured stdout/stderr from the sync script")


# ---------------------------------------------------------------------------
# Virtual Machines
# ---------------------------------------------------------------------------

class ProvisionRequest(BaseModel):
    """Request body for POST /vms/provision."""

    vm_name: str = Field(..., description="VM name: lowercase letters, digits, and hyphens, max 32 chars")
    ubuntu_version: Literal["2004", "2204", "2404"] = Field(..., description="Ubuntu version to provision")
    cpu: int = Field(..., ge=1, le=32, description="Number of vCPUs (1-32)")
    ram_mb: int = Field(..., ge=512, le=524288, description="RAM in MB (512-524288)")
    disk_gb: int = Field(..., ge=5, le=2000, description="Disk size in GB (5-2000)")
    ssh_public_key: str = Field(..., description="SSH public key to inject into the VM")
    network: str = Field("public", description="libvirt network name or 'macvtap'")
    ip_mode: Literal["dhcp", "static"] = Field("dhcp", description="IP assignment mode")
    static_ip: Optional[str] = Field(None, description="Static IP address (required when ip_mode=static)")
    subnet_mask: Optional[str] = Field("255.255.255.0", description="Subnet mask for static IP")
    gateway: Optional[str] = Field(None, description="Gateway IP (required when ip_mode=static)")
    dns: Optional[str] = Field("8.8.8.8", description="DNS server IP")
    storage_pool: Optional[str] = Field(None, description="Storage pool name (uses default if omitted)")
    source_type: Literal["base_image", "template"] = Field(
        "base_image", description="Source type for provisioning: base_image or template"
    )
    template_name: Optional[str] = Field(
        None, description="Template name to provision from (required when source_type=template)"
    )

    @field_validator("vm_name")
    @classmethod
    def validate_vm_name(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9][a-z0-9\-]{0,31}$", v):
            raise ValueError(
                "vm_name must be lowercase letters, digits, and hyphens only, max 32 chars"
            )
        return v

    @model_validator(mode="after")
    def validate_static_ip_fields(self) -> "ProvisionRequest":
        if self.ip_mode == "static":
            if not self.static_ip:
                raise ValueError("static_ip is required when ip_mode is 'static'")
            if not self.gateway:
                raise ValueError("gateway is required when ip_mode is 'static'")
        return self

    @model_validator(mode="after")
    def validate_template_fields(self) -> "ProvisionRequest":
        if self.source_type == "template":
            if not self.template_name or not self.template_name.strip():
                raise ValueError("template_name is required when source_type is 'template'")
        return self


class VMSummary(BaseModel):
    """Summary information for a VM shown in list views."""

    name: str
    state: str
    vcpus: int
    ram_mb: int
    ip: Optional[str] = None
    network: Optional[str] = None
    uptime: Optional[int] = None  # seconds since boot (best-effort)


class VMDetail(VMSummary):
    """Full VM details including CPU/RAM usage and VNC port."""

    cpu_percent: Optional[float] = None
    ram_used_mb: Optional[int] = None
    ram_total_mb: Optional[int] = None
    disk_gb: Optional[int] = None
    vnc_port: Optional[int] = None
    os_variant: Optional[str] = None


class ResizeRequest(BaseModel):
    """Request body for PATCH /vms/{name}/resize."""

    cpu: Optional[int] = Field(None, ge=1, le=32, description="New vCPU count")
    ram_mb: Optional[int] = Field(None, ge=512, le=524288, description="New RAM in MB")
    disk_gb: Optional[int] = Field(None, ge=5, le=2000, description="New disk size in GB")


class NetworkUpdateRequest(BaseModel):
    """Request body for PATCH /vms/{name}/network."""

    network: str = Field(..., description="Target network name or 'macvtap'")
    ip_mode: Literal["dhcp", "static"] = Field("dhcp", description="IP assignment mode")
    static_ip: Optional[str] = Field(None, description="Static IP address")
    subnet_mask: Optional[str] = Field("255.255.255.0", description="Subnet mask")
    gateway: Optional[str] = Field(None, description="Gateway IP")
    dns: Optional[str] = Field("8.8.8.8", description="DNS server IP")


class ProvisionResult(BaseModel):
    """Response body for POST /vms/provision."""

    vm_name: str
    status: str
    ip: Optional[str] = None
    vnc_port: Optional[int] = None
    network: str
    ip_mode: str
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

class SnapshotInfo(BaseModel):
    """Information about a single domain snapshot."""

    name: str
    created: Optional[str] = None
    description: Optional[str] = None
    state: Optional[str] = None
    is_current: bool = False


class SnapshotCreate(BaseModel):
    """Request body for POST /vms/{name}/snapshots."""

    name: str
    description: Optional[str] = None


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

class TemplateInfo(BaseModel):
    """Information about a standalone VM template (exported snapshot)."""

    name: str
    size: Optional[int] = None        # bytes of the .qcow2
    created: Optional[str] = None     # ISO-8601
    source_vm: Optional[str] = None
    source_snapshot: Optional[str] = None
    os_variant: Optional[str] = None


class TemplateExportRequest(BaseModel):
    """Request body for POST /vms/{name}/snapshots/{snap}/export."""

    template_name: str = Field(
        ...,
        pattern=r"^[a-z0-9][a-z0-9\-]{0,63}$",
        description="Template name: lowercase letters, digits, and hyphens, max 64 chars",
    )


# ---------------------------------------------------------------------------
# Host Stats
# ---------------------------------------------------------------------------

class HostStats(BaseModel):
    """Host-level resource utilisation percentages."""

    cpu_percent: float
    ram_percent: float
    disk_percent: float
    pool_percent: Optional[float] = None


# ---------------------------------------------------------------------------
# VM Stats
# ---------------------------------------------------------------------------

class VMStats(BaseModel):
    """Per-VM CPU and RAM utilisation."""

    cpu_percent: Optional[float] = None
    ram_percent: Optional[float] = None
    ram_used_mb: Optional[int] = None

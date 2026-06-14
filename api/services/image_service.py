"""Service layer for Ubuntu base-image management.

Responsibilities
----------------
- Enumerate locally cached base images and report their sync status vs upstream.
- Cache per-file SHA-256 digests to avoid recomputing on every request.
- Trigger a background sync via the host's ``sync-base-images.sh`` script.
- Track sync state in a small JSON status file.

Tests should monkeypatch:
    ``_compute_sha256``    — avoid reading real files
    ``_fetch_upstream_sha256`` — avoid real HTTP
    ``_launch_subprocess`` — avoid running the real sync script
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Optional
from urllib.request import urlopen
from urllib.error import URLError

from api import config
from api.schemas import ImageInfo, SyncStatus
from api.services import settings_service

# ---------------------------------------------------------------------------
# Version catalogue
# ---------------------------------------------------------------------------

# key → (codename, human label)
_VERSIONS: dict[str, tuple[str, str]] = {
    "2004": ("focal",  "Ubuntu 20.04 LTS"),
    "2204": ("jammy",  "Ubuntu 22.04 LTS"),
    "2404": ("noble",  "Ubuntu 24.04 LTS"),
}

VALID_VERSIONS: frozenset[str] = frozenset(_VERSIONS)


def _image_path(key: str) -> str:
    return os.path.join(config.BASE_IMAGE_DIR, f"ubuntu-{key}-base.img")


# ---------------------------------------------------------------------------
# SHA-256 helpers
# ---------------------------------------------------------------------------

def _read_cache() -> dict[str, str]:
    """Load the sha256 cache dict from disk.  Returns {} on any error."""
    try:
        with open(config.IMAGE_CACHE_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _write_cache(cache: dict[str, str]) -> None:
    parent = os.path.dirname(config.IMAGE_CACHE_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(config.IMAGE_CACHE_PATH, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, indent=2)


def _compute_sha256(path: str) -> str:
    """Return the hex SHA-256 digest of the file at *path*."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _cached_sha256(path: str, mtime: float, size: int) -> str:
    """Return the SHA-256 of *path*, using a cache keyed by ``path:mtime:size``.

    Recomputes only on a cache miss, then persists the updated cache.
    """
    cache_key = f"{path}:{mtime}:{size}"
    cache = _read_cache()
    if cache_key in cache:
        return cache[cache_key]
    digest = _compute_sha256(path)
    cache[cache_key] = digest
    try:
        _write_cache(cache)
    except OSError:
        pass  # Non-fatal — we still return the freshly computed digest
    return digest


def _fetch_upstream_sha256(codename: str) -> Optional[str]:
    """Fetch the upstream SHA-256 for ``<codename>-server-cloudimg-amd64.img``.

    Returns the hex digest string, or ``None`` if the fetch fails.
    """
    url = f"https://cloud-images.ubuntu.com/{codename}/current/SHA256SUMS"
    target = f"{codename}-server-cloudimg-amd64.img"
    try:
        with urlopen(url, timeout=5) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except (URLError, OSError, TimeoutError):
        return None

    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            # SHA256SUMS lines: "<hex>  <filename>" or "<hex> *<filename>"
            fname = parts[1].lstrip("*")
            if fname == target:
                return parts[0]
    return None


# ---------------------------------------------------------------------------
# Public API — list_images
# ---------------------------------------------------------------------------

def list_images() -> list[ImageInfo]:
    """Return info for all three Ubuntu base images."""
    results: list[ImageInfo] = []
    for key, (codename, label) in _VERSIONS.items():
        path = _image_path(key)
        if not os.path.exists(path):
            results.append(ImageInfo(
                version=key,
                codename=codename,
                label=label,
                status="missing",
                size=None,
                last_updated=None,
                checksum=None,
                id=key,
                source="ubuntu",
            ))
            continue

        stat = os.stat(path)
        size = stat.st_size
        mtime = stat.st_mtime
        last_updated = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()

        local_sha = _cached_sha256(path, mtime, size)
        upstream_sha = _fetch_upstream_sha256(codename)

        if upstream_sha is None:
            status = "unknown"
        elif local_sha == upstream_sha:
            status = "up_to_date"
        else:
            status = "outdated"

        results.append(ImageInfo(
            version=key,
            codename=codename,
            label=label,
            status=status,
            size=size,
            last_updated=last_updated,
            checksum=local_sha,
            id=key,
            source="ubuntu",
        ))

    # Custom images from settings
    for entry in settings_service.get_custom_images():
        path = os.path.join(config.BASE_IMAGE_DIR, entry["filename"])
        if os.path.exists(path):
            stat = os.stat(path)
            size = stat.st_size
            last_updated = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            status = "up_to_date"
        else:
            size = None
            last_updated = None
            status = "missing"
        results.append(ImageInfo(
            version=entry["id"],
            codename="custom",
            label=entry["label"],
            status=status,
            size=size,
            last_updated=last_updated,
            checksum=None,
            id=entry["id"],
            source="custom",
            os_variant=entry["os_variant"],
            url=entry["url"],
        ))

    return results


# ---------------------------------------------------------------------------
# Public API — custom image management
# ---------------------------------------------------------------------------

def add_custom_image(label: str, url: str, os_variant: str) -> dict:
    """Add a custom base image entry to settings and launch the download script.

    Args:
        label: Human-readable label for the image.
        url: URL to download the image from.
        os_variant: virt-install os-variant string.

    Returns:
        The entry dict that was persisted.

    Raises:
        ValueError: if the id is invalid, collides with a built-in, or already exists.
    """
    import re as _re

    # Slugify label → id
    slug = label.strip().lower()
    slug = _re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    if not slug or not _re.match(r"^[a-z0-9][a-z0-9-]{0,63}$", slug):
        raise ValueError(f"Label '{label}' produces invalid id '{slug}'")

    # Check collision with built-in keys
    if slug in VALID_VERSIONS:
        raise ValueError(f"Image id '{slug}' collides with a built-in Ubuntu version")

    # Check collision with existing custom ids
    existing = settings_service.get_custom_images()
    if any(e["id"] == slug for e in existing):
        raise ValueError(f"Custom image with id '{slug}' already exists")

    filename = f"custom-{slug}.qcow2"
    entry = {
        "id": slug,
        "label": label.strip(),
        "url": url,
        "os_variant": os_variant.strip(),
        "filename": filename,
    }
    settings_service.add_custom_image(entry)

    dest_path = os.path.join(config.BASE_IMAGE_DIR, filename)
    _launch_subprocess(["sudo", config.DOWNLOAD_SCRIPT, url, dest_path])

    return entry


def delete_custom_image(image_id: str) -> None:
    """Delete a custom image entry and best-effort remove its file.

    Raises:
        LookupError: if the image_id is not found in custom images.
    """
    existing = settings_service.get_custom_images()
    entry = next((e for e in existing if e["id"] == image_id), None)
    if entry is None:
        raise LookupError(f"Custom image '{image_id}' not found")

    # Best-effort file removal
    path = os.path.join(config.BASE_IMAGE_DIR, entry["filename"])
    try:
        os.remove(path)
    except OSError:
        pass

    settings_service.delete_custom_image(image_id)


def resolve_base_image(key: str) -> tuple[str, str]:
    """Resolve a base image key to (abs_image_path, os_variant).

    Args:
        key: built-in version key ('2004'/'2204'/'2404') or custom image id.

    Returns:
        Tuple of (absolute_image_path, os_variant_string).

    Raises:
        ValueError: if the key is not found in built-ins or custom images.
    """
    if key in _VERSIONS:
        return (_image_path(key), config.OS_VARIANTS[key])

    custom = settings_service.get_custom_images()
    entry = next((e for e in custom if e["id"] == key), None)
    if entry is not None:
        return (os.path.join(config.BASE_IMAGE_DIR, entry["filename"]), entry["os_variant"])

    raise ValueError(f"Unknown base image '{key}'")


# ---------------------------------------------------------------------------
# Public API — sync
# ---------------------------------------------------------------------------

def _read_status() -> dict:
    """Load the sync status dict.  Returns ``{"state": "idle"}`` on any error."""
    try:
        with open(config.IMAGE_SYNC_STATUS_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"state": "idle"}


def _write_status(data: dict) -> None:
    parent = os.path.dirname(config.IMAGE_SYNC_STATUS_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(config.IMAGE_SYNC_STATUS_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def _launch_subprocess(cmd: list[str]) -> None:
    """Launch *cmd* as a fire-and-forget background subprocess."""
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )


def trigger_sync(version: Optional[str] = None) -> dict:
    """Start the background sync script and record ``state=running``.

    Args:
        version: one of ``"2004"``, ``"2204"``, ``"2404"``, or ``None`` (sync all).

    Returns:
        The status dict written to disk (state = "running").
    """
    cmd = ["sudo", config.SYNC_SCRIPT]
    if version is not None:
        cmd.append(version)

    status: dict = {
        "state": "running",
        "version": version,
        "started_at": datetime.now(tz=timezone.utc).isoformat(),
        "finished_at": None,
        "returncode": None,
        "log": None,
    }
    _write_status(status)
    _launch_subprocess(cmd)
    return status


def get_sync_status() -> SyncStatus:
    """Return the current (or last-known) sync status."""
    raw = _read_status()
    return SyncStatus(
        state=raw.get("state", "idle"),
        version=raw.get("version"),
        started_at=raw.get("started_at"),
        finished_at=raw.get("finished_at"),
        returncode=raw.get("returncode"),
        log=raw.get("log"),
    )

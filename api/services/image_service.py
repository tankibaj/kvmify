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
        ))

    return results


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

"""Tests for the /images router and image_service."""
from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------

def _fake_stat(size: int = 512 * 1024 * 1024, mtime: float = 1_700_000_000.0):
    """Return a minimal os.stat_result-like mock."""
    s = MagicMock()
    s.st_size = size
    s.st_mtime = mtime
    return s


@pytest.fixture()
def tmp_image_paths(tmp_path, monkeypatch):
    """Redirect IMAGE_SYNC_STATUS_PATH and IMAGE_CACHE_PATH to tmp files,
    and patch BASE_IMAGE_DIR to a temporary directory."""
    from api import config

    base_dir = tmp_path / "base"
    base_dir.mkdir()
    status_file = tmp_path / "image-sync-status.json"
    cache_file = tmp_path / "image-sha256-cache.json"

    monkeypatch.setattr(config, "BASE_IMAGE_DIR", str(base_dir))
    monkeypatch.setattr(config, "IMAGE_SYNC_STATUS_PATH", str(status_file))
    monkeypatch.setattr(config, "IMAGE_CACHE_PATH", str(cache_file))

    return {
        "base_dir": base_dir,
        "status_file": status_file,
        "cache_file": cache_file,
    }


# ---------------------------------------------------------------------------
# GET /images — filesystem / checksum mocking
# ---------------------------------------------------------------------------

def test_list_images_all_missing(client: TestClient, tmp_image_paths):
    """GET /images returns three entries all marked 'missing' when no files exist."""
    # No image files created in tmp base_dir → all missing
    with patch("api.services.image_service._fetch_upstream_sha256", return_value=None):
        resp = client.get("/images")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    versions = {item["version"] for item in data}
    assert versions == {"2004", "2204", "2404"}
    for item in data:
        assert item["status"] == "missing"
        assert item["size"] is None
        assert item["checksum"] is None


def test_list_images_up_to_date(client: TestClient, tmp_image_paths):
    """GET /images returns 'up_to_date' when local sha matches upstream."""
    from api import config

    base_dir = tmp_image_paths["base_dir"]

    # Create fake image files for all three versions
    fake_sha = "abcdef1234567890" * 4  # 64-char hex
    for key in ("2004", "2204", "2404"):
        img = base_dir / f"ubuntu-{key}-base.img"
        img.write_bytes(b"\x00" * 1024)

    with (
        patch("api.services.image_service._compute_sha256", return_value=fake_sha),
        patch("api.services.image_service._fetch_upstream_sha256", return_value=fake_sha),
    ):
        resp = client.get("/images")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    for item in data:
        assert item["status"] == "up_to_date"
        assert item["checksum"] == fake_sha
        assert item["size"] is not None
        assert item["last_updated"] is not None


def test_list_images_outdated(client: TestClient, tmp_image_paths):
    """GET /images returns 'outdated' when local sha differs from upstream."""
    base_dir = tmp_image_paths["base_dir"]

    for key in ("2004", "2204", "2404"):
        img = base_dir / f"ubuntu-{key}-base.img"
        img.write_bytes(b"\x00" * 1024)

    local_sha = "aaaa" * 16
    upstream_sha = "bbbb" * 16

    with (
        patch("api.services.image_service._compute_sha256", return_value=local_sha),
        patch("api.services.image_service._fetch_upstream_sha256", return_value=upstream_sha),
    ):
        resp = client.get("/images")

    assert resp.status_code == 200
    for item in resp.json():
        assert item["status"] == "outdated"


def test_list_images_unknown_when_upstream_fails(client: TestClient, tmp_image_paths):
    """GET /images returns 'unknown' when upstream checksum fetch fails."""
    base_dir = tmp_image_paths["base_dir"]

    for key in ("2004", "2204", "2404"):
        img = base_dir / f"ubuntu-{key}-base.img"
        img.write_bytes(b"\x00" * 1024)

    with (
        patch("api.services.image_service._compute_sha256", return_value="aa" * 32),
        patch("api.services.image_service._fetch_upstream_sha256", return_value=None),
    ):
        resp = client.get("/images")

    assert resp.status_code == 200
    for item in resp.json():
        assert item["status"] == "unknown"


def test_list_images_mixed_statuses(client: TestClient, tmp_image_paths):
    """GET /images handles a mix of present and missing images correctly."""
    base_dir = tmp_image_paths["base_dir"]

    # Only create the 2204 image
    img = base_dir / "ubuntu-2204-base.img"
    img.write_bytes(b"\x00" * 1024)

    sha = "cc" * 32

    with (
        patch("api.services.image_service._compute_sha256", return_value=sha),
        patch("api.services.image_service._fetch_upstream_sha256", return_value=sha),
    ):
        resp = client.get("/images")

    assert resp.status_code == 200
    data = resp.json()
    by_ver = {item["version"]: item for item in data}
    assert by_ver["2204"]["status"] == "up_to_date"
    assert by_ver["2004"]["status"] == "missing"
    assert by_ver["2404"]["status"] == "missing"


# ---------------------------------------------------------------------------
# SHA-256 cache
# ---------------------------------------------------------------------------

def test_sha256_cache_used_on_second_call(tmp_image_paths):
    """_cached_sha256 calls _compute_sha256 once then uses the cache."""
    from api.services.image_service import _cached_sha256

    with patch("api.services.image_service._compute_sha256", return_value="dd" * 32) as mock_compute:
        r1 = _cached_sha256("/fake/path.img", 100.0, 1024)
        r2 = _cached_sha256("/fake/path.img", 100.0, 1024)

    assert r1 == r2 == "dd" * 32
    mock_compute.assert_called_once()  # second call hit the cache


# ---------------------------------------------------------------------------
# POST /images/sync
# ---------------------------------------------------------------------------

def test_sync_returns_running(client: TestClient, tmp_image_paths):
    """POST /images/sync returns state=running without launching a real process."""
    with patch("api.services.image_service._launch_subprocess") as mock_launch:
        resp = client.post("/images/sync", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "running"
    assert data["version"] is None
    assert data["started_at"] is not None
    mock_launch.assert_called_once()


def test_sync_with_valid_version(client: TestClient, tmp_image_paths):
    """POST /images/sync with version='2204' passes the key to the script."""
    with patch("api.services.image_service._launch_subprocess") as mock_launch:
        resp = client.post("/images/sync", json={"version": "2204"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "running"
    assert data["version"] == "2204"
    # The command passed to _launch_subprocess should include the version key
    cmd = mock_launch.call_args[0][0]
    assert "2204" in cmd


def test_sync_invalid_version_returns_400(client: TestClient, tmp_image_paths):
    """POST /images/sync with an unrecognised version returns 400."""
    with patch("api.services.image_service._launch_subprocess"):
        resp = client.post("/images/sync", json={"version": "9999"})

    assert resp.status_code == 400


def test_sync_status_written_to_disk(client: TestClient, tmp_image_paths):
    """POST /images/sync writes the running status to IMAGE_SYNC_STATUS_PATH."""
    from api import config

    with patch("api.services.image_service._launch_subprocess"):
        client.post("/images/sync", json={"version": "2404"})

    assert os.path.exists(config.IMAGE_SYNC_STATUS_PATH)
    with open(config.IMAGE_SYNC_STATUS_PATH) as fh:
        saved = json.load(fh)
    assert saved["state"] == "running"
    assert saved["version"] == "2404"


# ---------------------------------------------------------------------------
# GET /images/sync/status
# ---------------------------------------------------------------------------

def test_sync_status_idle_when_no_file(client: TestClient, tmp_image_paths):
    """GET /images/sync/status returns state=idle when status file absent."""
    resp = client.get("/images/sync/status")
    assert resp.status_code == 200
    assert resp.json()["state"] == "idle"


def test_sync_status_reflects_written_file(client: TestClient, tmp_image_paths):
    """GET /images/sync/status reflects whatever is in the status file."""
    from api import config

    payload = {
        "state": "finished",
        "version": "2004",
        "started_at": "2024-01-01T00:00:00+00:00",
        "finished_at": "2024-01-01T00:05:00+00:00",
        "returncode": 0,
        "log": "done",
    }
    os.makedirs(os.path.dirname(config.IMAGE_SYNC_STATUS_PATH), exist_ok=True)
    with open(config.IMAGE_SYNC_STATUS_PATH, "w") as fh:
        json.dump(payload, fh)

    resp = client.get("/images/sync/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "finished"
    assert data["returncode"] == 0
    assert data["log"] == "done"


def test_sync_flow_post_then_status(client: TestClient, tmp_image_paths):
    """Full flow: POST /images/sync → GET /images/sync/status returns running."""
    with patch("api.services.image_service._launch_subprocess"):
        client.post("/images/sync", json={})

    resp = client.get("/images/sync/status")
    assert resp.status_code == 200
    assert resp.json()["state"] == "running"


# ---------------------------------------------------------------------------
# Custom images — POST /images
# ---------------------------------------------------------------------------

def test_add_custom_image_returns_201(client: TestClient, tmp_image_paths, tmp_settings):
    """POST /images with valid body returns 201 and the entry dict."""
    with patch("api.services.image_service._launch_subprocess") as mock_launch:
        resp = client.post("/images", json={
            "label": "Debian 12",
            "url": "https://example.com/debian-12.qcow2",
            "os_variant": "debian12",
        })

    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == "debian-12"
    assert data["label"] == "Debian 12"
    assert data["url"] == "https://example.com/debian-12.qcow2"
    assert data["os_variant"] == "debian12"
    assert data["filename"] == "custom-debian-12.qcow2"

    # _launch_subprocess called with sudo + DOWNLOAD_SCRIPT + url + dest
    mock_launch.assert_called_once()
    cmd = mock_launch.call_args[0][0]
    assert cmd[0] == "sudo"
    assert "download-base-image.sh" in cmd[1]
    assert cmd[2] == "https://example.com/debian-12.qcow2"
    assert "custom-debian-12.qcow2" in cmd[3]


def test_add_custom_image_appears_in_list(client: TestClient, tmp_image_paths, tmp_settings):
    """After POST /images, GET /images includes the custom image with source=='custom'."""
    with patch("api.services.image_service._launch_subprocess"):
        client.post("/images", json={
            "label": "Debian 12",
            "url": "https://example.com/debian-12.qcow2",
            "os_variant": "debian12",
        })

    with patch("api.services.image_service._fetch_upstream_sha256", return_value=None):
        resp = client.get("/images")

    assert resp.status_code == 200
    data = resp.json()
    custom = [img for img in data if img.get("source") == "custom"]
    assert len(custom) == 1
    assert custom[0]["id"] == "debian-12"
    assert custom[0]["source"] == "custom"
    assert custom[0]["status"] == "missing"  # file not present on disk


def test_add_custom_image_status_up_to_date_when_file_exists(client: TestClient, tmp_image_paths, tmp_settings):
    """GET /images shows 'up_to_date' for a custom image when its file exists."""
    from api import config

    # Add the custom image entry
    with patch("api.services.image_service._launch_subprocess"):
        client.post("/images", json={
            "label": "Debian 12",
            "url": "https://example.com/debian-12.qcow2",
            "os_variant": "debian12",
        })

    # Create the file
    img_path = os.path.join(config.BASE_IMAGE_DIR, "custom-debian-12.qcow2")
    with open(img_path, "wb") as f:
        f.write(b"\x00" * 1024)

    with patch("api.services.image_service._fetch_upstream_sha256", return_value=None):
        resp = client.get("/images")

    custom = [img for img in resp.json() if img.get("source") == "custom"]
    assert custom[0]["status"] == "up_to_date"
    assert custom[0]["size"] is not None


def test_add_custom_image_duplicate_id_returns_409(client: TestClient, tmp_image_paths, tmp_settings):
    """POST /images with a label that produces the same id as an existing custom image returns 409."""
    with patch("api.services.image_service._launch_subprocess"):
        client.post("/images", json={
            "label": "Debian 12",
            "url": "https://example.com/debian-12.qcow2",
            "os_variant": "debian12",
        })

    # Same label again → same id collision
    with patch("api.services.image_service._launch_subprocess"):
        resp = client.post("/images", json={
            "label": "Debian 12",
            "url": "https://example.com/other.qcow2",
            "os_variant": "debian12",
        })

    assert resp.status_code == 409


def test_add_custom_image_collision_with_builtin_returns_409_or_400(client: TestClient, tmp_image_paths, tmp_settings):
    """POST /images with a label that slugifies to a built-in key (e.g. '2204') returns 409 or 400."""
    with patch("api.services.image_service._launch_subprocess"):
        resp = client.post("/images", json={
            "label": "2204",
            "url": "https://example.com/img.qcow2",
            "os_variant": "ubuntu22.04",
        })

    assert resp.status_code in (400, 409)


def test_add_custom_image_invalid_url_returns_422(client: TestClient, tmp_image_paths, tmp_settings):
    """POST /images with a non-http(s) URL returns 422 (Pydantic validation)."""
    resp = client.post("/images", json={
        "label": "Bad Image",
        "url": "ftp://example.com/img.qcow2",
        "os_variant": "debian12",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Custom images — DELETE /images/{id}
# ---------------------------------------------------------------------------

def test_delete_custom_image_returns_204(client: TestClient, tmp_image_paths, tmp_settings):
    """DELETE /images/{id} returns 204 and removes the entry from settings."""
    from api.services import settings_service

    with patch("api.services.image_service._launch_subprocess"):
        client.post("/images", json={
            "label": "Debian 12",
            "url": "https://example.com/debian-12.qcow2",
            "os_variant": "debian12",
        })

    with patch("api.services.image_service.os.remove"):
        resp = client.delete("/images/debian-12")

    assert resp.status_code == 204
    remaining = settings_service.get_custom_images()
    assert not any(e["id"] == "debian-12" for e in remaining)


def test_delete_builtin_image_returns_400(client: TestClient, tmp_image_paths, tmp_settings):
    """DELETE /images/2204 returns 400 (cannot delete built-in)."""
    resp = client.delete("/images/2204")
    assert resp.status_code == 400


def test_delete_unknown_custom_image_returns_404(client: TestClient, tmp_image_paths, tmp_settings):
    """DELETE /images/nonexistent returns 404."""
    resp = client.delete("/images/nonexistent-image")
    assert resp.status_code == 404

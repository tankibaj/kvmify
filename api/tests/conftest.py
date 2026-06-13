"""Shared pytest fixtures for the KVMify backend test suite.

Key fixtures
------------
client
    A :class:`fastapi.testclient.TestClient` wrapping the FastAPI app.

mock_conn
    A :class:`unittest.mock.MagicMock` that mimics a ``libvirt.virConnect``
    object.  Use with ``patch_libvirt`` to inject it into the application.

patch_libvirt
    A pytest fixture (function scope) that monkeypatches
    ``api.services.libvirt_service.connect`` **and**
    ``api.services.libvirt_service.connection`` so no real libvirt daemon is
    ever contacted during tests.

    The ``connection`` context manager is replaced by a simple
    ``contextmanager`` that yields the mock connection directly.

tmp_settings
    Redirects ``api.config.SETTINGS_PATH`` to a temporary file so settings
    tests never touch the real ``kvmify-settings.json``.
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api import config
from api.main import app


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client() -> TestClient:
    """Session-scoped TestClient — cheap to share across tests."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# libvirt mock helpers
# ---------------------------------------------------------------------------

def make_mock_conn() -> MagicMock:
    """Build and return a fresh MagicMock posing as a libvirt connection."""
    conn = MagicMock(name="libvirt.virConnect")
    conn.close = MagicMock()
    conn.listAllNetworks = MagicMock(return_value=[])
    conn.listAllStoragePools = MagicMock(return_value=[])
    conn.storagePoolLookupByName = MagicMock(side_effect=Exception("pool not found"))
    conn.storagePoolDefineXML = MagicMock()
    return conn


@pytest.fixture()
def mock_conn() -> MagicMock:
    """Return a fresh mock libvirt connection for each test."""
    return make_mock_conn()


@pytest.fixture()
def patch_libvirt(mock_conn: MagicMock):
    """Monkeypatch libvirt_service so no real libvirt daemon is contacted.

    Patches both ``connect`` (for code that calls it directly) **and**
    ``connection`` (the context manager) to return/yield *mock_conn*.

    Usage::

        def test_something(client, patch_libvirt, mock_conn):
            mock_conn.listAllNetworks.return_value = [...]
            resp = client.get("/networks")
    """
    _conn = mock_conn

    @contextmanager
    def _fake_connection() -> Generator:
        yield _conn

    with (
        patch("api.services.libvirt_service.connect", return_value=_conn),
        patch("api.services.libvirt_service.connection", _fake_connection),
    ):
        yield _conn


# ---------------------------------------------------------------------------
# Settings isolation
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_settings(tmp_path, monkeypatch):
    """Redirect SETTINGS_PATH to a temp file for the duration of a test.

    Also patches ``api.services.settings_service`` so it reads ``config.SETTINGS_PATH``
    dynamically (which it already does), and wipes the imported module's cached
    state if any.

    Returns the path to the temporary settings file.
    """
    settings_file = tmp_path / "kvmify-settings.json"
    monkeypatch.setattr(config, "SETTINGS_PATH", str(settings_file))
    return settings_file

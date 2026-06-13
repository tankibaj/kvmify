"""Persists KVMify application settings to a JSON file.

Currently stores:
  - ``default_pool``: name of the libvirt storage pool used when provisioning
    a VM without an explicit pool selection.

The file location is controlled by ``config.SETTINGS_PATH``.  If the file or
its parent directory does not exist they are created on first write.  If the
file is missing or the key is absent, ``default_pool`` seeds to ``"default"``.
"""
from __future__ import annotations

import json
import os
from typing import Any

from api import config

_DEFAULT_POOL = "default"


def _read() -> dict[str, Any]:
    """Read and return the settings dict from disk.  Returns {} on any error."""
    try:
        with open(config.SETTINGS_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write(data: dict[str, Any]) -> None:
    """Persist *data* to the settings file, creating parent dirs as needed."""
    parent = os.path.dirname(config.SETTINGS_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(config.SETTINGS_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def get_settings() -> dict[str, Any]:
    """Return the full settings dictionary."""
    settings = _read()
    # Ensure default_pool is always present
    settings.setdefault("default_pool", _DEFAULT_POOL)
    return settings


def get_default_pool() -> str:
    """Return the name of the default storage pool (never empty)."""
    return _read().get("default_pool", _DEFAULT_POOL)


def set_default_pool(name: str) -> None:
    """Persist *name* as the default storage pool.

    Args:
        name: libvirt storage pool name to set as default.
    """
    data = _read()
    data["default_pool"] = name
    _write(data)

"""Host-level stats: CPU, RAM, disk utilisation via psutil."""
from __future__ import annotations

import os

import psutil

from api import config


def get_host_stats() -> dict:
    """Return host-level resource usage percentages.

    Uses psutil to sample CPU %, RAM %, root-disk %, and pool-disk %.
    If the pool disk path does not exist (e.g. NVMe not mounted) pool_percent
    is set to None rather than raising.

    Returns:
        dict with keys: cpu_percent, ram_percent, disk_percent, pool_percent
    """
    cpu_percent = round(psutil.cpu_percent(interval=0.3), 1)
    ram_percent = round(psutil.virtual_memory().percent, 1)
    disk_percent = round(psutil.disk_usage(config.HOST_DISK_PATH).percent, 1)

    pool_percent: float | None = None
    if os.path.exists(config.POOL_DISK_PATH):
        try:
            pool_percent = round(psutil.disk_usage(config.POOL_DISK_PATH).percent, 1)
        except (PermissionError, OSError):
            pool_percent = None

    return {
        "cpu_percent": cpu_percent,
        "ram_percent": ram_percent,
        "disk_percent": disk_percent,
        "pool_percent": pool_percent,
    }

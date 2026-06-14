"""Host-level stats: CPU, RAM, disk utilisation via psutil."""
from __future__ import annotations

import os

import psutil

from api import config


_GB = 1024 ** 3


def get_host_stats() -> dict:
    """Return host-level resource usage: percentages plus absolute GB.

    Uses psutil to sample CPU %, RAM %, root-disk %, and pool-disk %, and to
    report RAM/disk used+total in GB and the logical CPU count (the denominator
    for "vCPUs allocated / cores" on the dashboard).  If the pool disk path does
    not exist (e.g. NVMe not mounted) pool_percent is set to None rather than
    raising.
    """
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(config.HOST_DISK_PATH)

    cpu_percent = round(psutil.cpu_percent(interval=0.3), 1)
    ram_percent = round(mem.percent, 1)
    disk_percent = round(disk.percent, 1)

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
        "ram_used_gb": round(mem.used / _GB, 1),
        "ram_total_gb": round(mem.total / _GB, 1),
        "disk_used_gb": round(disk.used / _GB, 1),
        "disk_total_gb": round(disk.total / _GB, 1),
        "host_cpu_count": psutil.cpu_count(logical=True) or 1,
    }

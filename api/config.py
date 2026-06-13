"""Central configuration — every value is env-overridable."""
import os

# libvirt connection URI — must be qemu:///system for host-level access
LIBVIRT_URI: str = os.getenv("KVMIFY_LIBVIRT_URI", "qemu:///system")

# Directory containing read-only Ubuntu base images
BASE_IMAGE_DIR: str = os.getenv("KVMIFY_BASE_DIR", "/mnt/nvme1/kvm/pool/base")

# Path to KVMify's own settings file (persists default_pool, etc.)
SETTINGS_PATH: str = os.getenv(
    "KVMIFY_SETTINGS", "/home/naim/kvmify/api/kvmify-settings.json"
)

# Path to the base-image sync script
SYNC_SCRIPT: str = os.getenv(
    "KVMIFY_SYNC_SCRIPT", "/usr/local/bin/sync-base-images.sh"
)

# Path to the image-sync status JSON file (written by trigger_sync, read by get_sync_status)
_SETTINGS_DIR: str = os.path.dirname(
    os.getenv("KVMIFY_SETTINGS", "/home/naim/kvmify/api/kvmify-settings.json")
)
IMAGE_SYNC_STATUS_PATH: str = os.getenv(
    "KVMIFY_IMAGE_SYNC_STATUS",
    os.path.join(_SETTINGS_DIR, "image-sync-status.json"),
)

# Path to the per-image sha256 cache JSON file
IMAGE_CACHE_PATH: str = os.getenv(
    "KVMIFY_IMAGE_CACHE",
    os.path.join(_SETTINGS_DIR, "image-sha256-cache.json"),
)

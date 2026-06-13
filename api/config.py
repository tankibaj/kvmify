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

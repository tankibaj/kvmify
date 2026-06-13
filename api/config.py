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

# ---------------------------------------------------------------------------
# VM provisioning
# ---------------------------------------------------------------------------

# Path to the provision-vm.sh script installed on the host
PROVISION_SCRIPT: str = os.getenv(
    "KVMIFY_PROVISION_SCRIPT", "/usr/local/bin/provision-vm.sh"
)

# Physical NIC used for macvtap (direct) networking
PHYSICAL_NIC: str = os.getenv("KVMIFY_PHYSICAL_NIC", "enp4s0")

# Directory where cloud-init seed input files are written before provisioning
SEED_DIR: str = os.getenv("KVMIFY_SEED_DIR", "/home/naim/kvmify/seeds")

# Fallback disk directory if pool lookup fails
VM_DISK_DIR: str = os.getenv("KVMIFY_VM_DISK_DIR", "/mnt/nvme1/kvm/pool/vms")

# Ubuntu version → virt-install os-variant string
OS_VARIANTS: dict[str, str] = {
    "2004": "ubuntu20.04",
    "2204": "ubuntu22.04",
    "2404": "ubuntu24.04",
}

# Ubuntu version → base image filename under BASE_IMAGE_DIR
BASE_IMAGE_NAMES: dict[str, str] = {
    "2004": "ubuntu-2004-base.img",
    "2204": "ubuntu-2204-base.img",
    "2404": "ubuntu-2404-base.img",
}

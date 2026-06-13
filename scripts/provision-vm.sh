#!/usr/bin/env bash
# provision-vm.sh — create and launch a KVM VM from a cloud base image
#
# Usage:
#   provision-vm.sh <vm_name> <base_img_path> <disk_path> <disk_gb> \
#                   <cpu> <ram_mb> <network_arg> <os_variant> \
#                   <userdata_path> [networkconfig_path]
#
# Arguments (positional):
#   1  vm_name            Name for the new VM domain
#   2  base_img_path      Full path to the read-only backing base image
#   3  disk_path          Full path where the new qcow2 disk will be created
#   4  disk_gb            Disk size in GB (integer)
#   5  cpu                Number of vCPUs
#   6  ram_mb             RAM in megabytes
#   7  network_arg        virt-install --network value
#                         (e.g. "network=default" or
#                          "type=direct,source=enp4s0,source_mode=bridge")
#   8  os_variant         OS variant for virt-install (e.g. ubuntu22.04)
#   9  userdata_path      Path to cloud-init user-data YAML file
#  10  networkconfig_path (optional) Path to cloud-init network-config YAML

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

if [[ $# -lt 9 ]]; then
    echo "ERROR: insufficient arguments" >&2
    echo "Usage: $0 <vm_name> <base_img_path> <disk_path> <disk_gb> <cpu> <ram_mb> <network_arg> <os_variant> <userdata_path> [networkconfig_path]" >&2
    exit 1
fi

VM_NAME="$1"
BASE_IMG_PATH="$2"
DISK_PATH="$3"
DISK_GB="$4"
CPU="$5"
RAM_MB="$6"
NETWORK_ARG="$7"
OS_VARIANT="$8"
USERDATA_PATH="$9"
NETWORKCONFIG_PATH="${10:-}"

# ---------------------------------------------------------------------------
# Validate inputs
# ---------------------------------------------------------------------------

echo "[provision-vm] Starting provisioning for VM: ${VM_NAME}"

if [[ ! -f "${BASE_IMG_PATH}" ]]; then
    echo "ERROR: Base image not found: ${BASE_IMG_PATH}" >&2
    exit 1
fi

if [[ ! -f "${USERDATA_PATH}" ]]; then
    echo "ERROR: user-data file not found: ${USERDATA_PATH}" >&2
    exit 1
fi

if [[ -n "${NETWORKCONFIG_PATH}" && ! -f "${NETWORKCONFIG_PATH}" ]]; then
    echo "ERROR: network-config file not found: ${NETWORKCONFIG_PATH}" >&2
    exit 1
fi

# Ensure disk directory exists
DISK_DIR="$(dirname "${DISK_PATH}")"
mkdir -p "${DISK_DIR}"

# ---------------------------------------------------------------------------
# Step 1: Create overlay qcow2 disk
# ---------------------------------------------------------------------------

echo "[provision-vm] Creating overlay disk: ${DISK_PATH} (${DISK_GB}G backed by ${BASE_IMG_PATH})"
qemu-img create -f qcow2 -b "${BASE_IMG_PATH}" -F qcow2 "${DISK_PATH}" "${DISK_GB}G"

# ---------------------------------------------------------------------------
# Step 2: Create cloud-init seed ISO
# ---------------------------------------------------------------------------

SEED_PATH="${DISK_PATH%.qcow2}-seed.iso"
echo "[provision-vm] Creating cloud-init seed ISO: ${SEED_PATH}"

if [[ -n "${NETWORKCONFIG_PATH}" ]]; then
    cloud-localds "${SEED_PATH}" "${USERDATA_PATH}" --network-config "${NETWORKCONFIG_PATH}"
else
    cloud-localds "${SEED_PATH}" "${USERDATA_PATH}"
fi

# ---------------------------------------------------------------------------
# Step 3: Install / launch the VM
# ---------------------------------------------------------------------------

echo "[provision-vm] Running virt-install for VM: ${VM_NAME}"
virt-install \
    --import \
    --name "${VM_NAME}" \
    --memory "${RAM_MB}" \
    --vcpus "${CPU}" \
    --disk path="${DISK_PATH}",format=qcow2,bus=virtio \
    --disk path="${SEED_PATH}",device=cdrom \
    --os-variant "${OS_VARIANT}" \
    --network "${NETWORK_ARG}" \
    --graphics vnc,listen=127.0.0.1 \
    --noautoconsole

echo "[provision-vm] VM '${VM_NAME}' provisioned successfully."

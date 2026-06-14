#!/usr/bin/env bash
# export-vm-snapshot.sh — export an internal qcow2 snapshot as a standalone template
#
# Usage:
#   export-vm-snapshot.sh <source_disk_path> <snapshot_name> <dest_qcow2_path>
#
# Arguments (positional):
#   1  source_disk_path   Full path to the VM's qcow2 disk file
#   2  snapshot_name      Internal qcow2 snapshot name to export
#   3  dest_qcow2_path    Full path where the standalone template will be written

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

if [[ $# -lt 3 ]]; then
    echo "ERROR: insufficient arguments" >&2
    echo "Usage: $0 <source_disk_path> <snapshot_name> <dest_qcow2_path>" >&2
    exit 1
fi

SRC="$1"
SNAP="$2"
DEST="$3"
DEST_DIR="$(dirname "$DEST")"

# ---------------------------------------------------------------------------
# Validate inputs
# ---------------------------------------------------------------------------

echo "[export-vm-snapshot] Exporting snapshot '${SNAP}' from ${SRC} -> ${DEST}"

if [[ ! -e "${SRC}" ]]; then
    echo "ERROR: source disk not found: ${SRC}" >&2
    exit 1
fi

mkdir -p "${DEST_DIR}"

# ---------------------------------------------------------------------------
# Export: flatten snapshot into standalone qcow2
# -U: allow reading while the VM may be running (snapshot state is immutable)
# ---------------------------------------------------------------------------

qemu-img convert -U -O qcow2 -l "snapshot.name=${SNAP}" "${SRC}" "${DEST}"

chown naim:naim "${DEST}"
chmod 644 "${DEST}"

# Best effort: keep templates dir owned by naim so listing/deletion is unprivileged
chown naim:naim "${DEST_DIR}" 2>/dev/null || true

echo "[export-vm-snapshot] Exported ${SRC}@${SNAP} -> ${DEST}"

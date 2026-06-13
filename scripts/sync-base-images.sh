#!/usr/bin/env bash
#
# sync-base-images.sh — checksum-based sync of Ubuntu cloud base images for KVMify.
#
# Downloads Ubuntu server cloud images only when the upstream SHA256 differs from
# the local copy (or the local copy is missing), verifies the checksum, installs
# the image read-only (chmod 444) into the base-image directory.
#
# Usage:
#   sync-base-images.sh                # sync all versions
#   sync-base-images.sh 2404           # sync only one (2004 | 2204 | 2404)
#
# Env:
#   KVMIFY_BASE_DIR   base image dir (default: /mnt/nvme1/kvm/pool/base)
#
# Run as root (writes to a root-owned pool dir). Designed for cron + manual use.

set -euo pipefail

BASE_DIR="${KVMIFY_BASE_DIR:-/mnt/nvme1/kvm/pool/base}"
MIRROR="https://cloud-images.ubuntu.com"

# version key -> "codename"
declare -A CODENAME=(
  [2004]="focal"
  [2204]="jammy"
  [2404]="noble"
)

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
err() { log "ERROR: $*" >&2; }

# sha256 of a local file (empty string if absent)
local_sha() {
  local f="$1"
  [[ -f "$f" ]] || { echo ""; return; }
  sha256sum "$f" | awk '{print $1}'
}

sync_one() {
  local key="$1"
  local codename="${CODENAME[$key]}"
  local img="${codename}-server-cloudimg-amd64.img"
  local url="${MIRROR}/${codename}/current/${img}"
  local sums_url="${MIRROR}/${codename}/current/SHA256SUMS"
  local dest="${BASE_DIR}/ubuntu-${key}-base.img"

  log "Checking ubuntu-${key} (${codename})..."

  # Fetch upstream checksum for this image
  local expected
  expected="$(curl -fsSL "$sums_url" | awk -v f="*${img}" '$2==f {print $1}')"
  if [[ -z "$expected" ]]; then
    err "could not find ${img} in ${sums_url}"
    return 1
  fi

  # Up to date?
  if [[ "$(local_sha "$dest")" == "$expected" ]]; then
    log "ubuntu-${key} up to date (${expected:0:12}…), skipping."
    return 0
  fi

  # Download to a temp file alongside dest, verify, then install atomically.
  log "Downloading ${url}"
  local tmp
  tmp="$(mktemp "${BASE_DIR}/.${key}.XXXXXX.img")"
  trap 'rm -f "$tmp"' RETURN
  curl -fSL --retry 3 -o "$tmp" "$url"

  local got
  got="$(sha256sum "$tmp" | awk '{print $1}')"
  if [[ "$got" != "$expected" ]]; then
    err "checksum mismatch for ubuntu-${key}: got ${got}, expected ${expected}"
    return 1
  fi

  chmod 444 "$tmp"
  mv -f "$tmp" "$dest"
  trap - RETURN
  log "Installed ${dest} (sha256 ${expected:0:12}…)"
}

main() {
  mkdir -p "$BASE_DIR"

  local keys=()
  if [[ $# -gt 0 ]]; then
    local arg="${1//./}"   # accept 24.04 or 2404
    arg="${arg#ubuntu-}"
    if [[ -z "${CODENAME[$arg]:-}" ]]; then
      err "unknown version '$1' (valid: ${!CODENAME[*]})"
      exit 2
    fi
    keys=("$arg")
  else
    keys=(2004 2204 2404)
  fi

  local rc=0
  for k in "${keys[@]}"; do
    sync_one "$k" || rc=1
  done

  log "Sync complete (exit ${rc})."
  return $rc
}

main "$@"

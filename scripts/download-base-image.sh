#!/usr/bin/env bash
# download-base-image.sh — Download a cloud image from URL to DEST.
#
# Usage: sudo /usr/local/bin/download-base-image.sh <URL> <DEST>
#
# Required sudoers line (add to /etc/sudoers.d/kvmify):
#   naim ALL=(ALL) NOPASSWD: /usr/local/bin/download-base-image.sh
#
set -euo pipefail

URL="$1"
DEST="$2"
DEST_DIR="$(dirname "$DEST")"

mkdir -p "$DEST_DIR"
TMP="$(mktemp "${DEST}.XXXXXX")"

curl -fSL --connect-timeout 20 -o "$TMP" "$URL"
chown naim:naim "$TMP" || true
chmod 644 "$TMP"
mv -f "$TMP" "$DEST"

echo "[download-base-image] saved $DEST"

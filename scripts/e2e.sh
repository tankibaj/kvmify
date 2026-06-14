#!/usr/bin/env bash
#
# e2e.sh — run KVMify's Playwright UI E2E tests for every workflow.
#
# Pure browser tests: they drive the deployed UI and create/clean up their own
# throwaway resources THROUGH THE UI/API (prefix `kvmify-e2e-`). Production VMs
# are never touched (see ⛔ PRODUCTION SAFETY in CLAUDE.md).
#
#   • Headless by default; --headed shows the browser (needs a display).
#   • Runs from the KVM host (target 127.0.0.1) or from a dev machine / Mac.
#
# Reaching the host's UI from a Mac:
#   Browsing http://192.168.178.101 directly may fail under automation with
#   net::ERR_ADDRESS_UNREACHABLE — macOS "Local Network" privacy permission and
#   Chrome's Local Network Access block automated LAN access. The robust fix is
#   --tunnel: it opens an SSH tunnel and points the browser at 127.0.0.1, which
#   is never blocked. (See web-ui/e2e/README.md → Troubleshooting.)
#
# Usage:
#   scripts/e2e.sh [options] [-- <extra playwright args>]
#
# Options:
#   --tunnel            SSH-forward the host UI to 127.0.0.1 and test through it
#                       (recommended from a Mac — avoids LAN-access blocks).
#   --host <ssh-target> SSH target for --tunnel (default: naim@192.168.178.101).
#   --headed            Run with a visible browser (requires a display).
#   --base-url <url>    UI to test (default: http://192.168.178.101).
#   --grep <pattern>    Only run tests whose title matches <pattern>.
#   -h, --help          Show this help.
#
# Examples:
#   scripts/e2e.sh --tunnel              # from your Mac: all workflows, headless
#   scripts/e2e.sh --tunnel --headed     # watch it in a browser
#   ./scripts/e2e.sh --base-url http://127.0.0.1   # on the KVM host
#   scripts/e2e.sh --tunnel --grep "VM workflows"
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_UI_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)/web-ui"

BASE_URL="${PLAYWRIGHT_BASE_URL:-http://192.168.178.101}"
HOST_SSH="${KVMIFY_SSH:-naim@192.168.178.101}"
TUNNEL=0
TUNNEL_PORT="${KVMIFY_TUNNEL_PORT:-8888}"
HEADED=0
GREP=""
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tunnel)     TUNNEL=1; shift ;;
    --host)       HOST_SSH="$2"; shift 2 ;;
    --headed)     HEADED=1; shift ;;
    --base-url)   BASE_URL="$2"; shift 2 ;;
    --grep)       GREP="$2"; shift 2 ;;
    -h|--help)    sed -n '2,34p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    --)           shift; EXTRA_ARGS+=("$@"); break ;;
    *)            EXTRA_ARGS+=("$1"); shift ;;
  esac
done

# Open an SSH tunnel so the browser hits the UI over loopback (never LAN-blocked).
TUNNEL_PID=""
cleanup() { [[ -n "${TUNNEL_PID}" ]] && kill "${TUNNEL_PID}" 2>/dev/null || true; }
trap cleanup EXIT

if [[ "${TUNNEL}" -eq 1 ]]; then
  echo "▶ SSH tunnel: 127.0.0.1:${TUNNEL_PORT} → ${HOST_SSH} (host nginx :80)"
  if ! ssh -fN -o ExitOnForwardFailure=yes -L "${TUNNEL_PORT}:127.0.0.1:80" "${HOST_SSH}"; then
    echo "  ✖ Failed to open SSH tunnel to ${HOST_SSH}." >&2
    exit 1
  fi
  TUNNEL_PID="$(pgrep -f "${TUNNEL_PORT}:127.0.0.1:80 ${HOST_SSH}" | head -1 || true)"
  BASE_URL="http://127.0.0.1:${TUNNEL_PORT}"
  sleep 1
fi

export PLAYWRIGHT_BASE_URL="${BASE_URL}"

# A headed run needs a display; the KVM host has none.
if [[ "${HEADED}" -eq 1 && -z "${DISPLAY:-}" && "$(uname)" != "Darwin" ]]; then
  echo "⚠ --headed requested but no display detected — forcing headless." >&2
  HEADED=0
fi

echo "▶ Target UI: ${BASE_URL}"
if ! curl -fsS -o /dev/null --max-time 8 "${BASE_URL}" 2>/dev/null; then
  echo "  ✖ UI not reachable at ${BASE_URL}. Is KVMify deployed and running?" >&2
  [[ "${TUNNEL}" -eq 0 ]] && echo "    From a Mac, try: scripts/e2e.sh --tunnel" >&2
  exit 1
fi

cd "${WEB_UI_DIR}"
if [[ ! -d node_modules ]]; then
  echo "▶ Installing npm deps…"
  npm ci || npm install
fi
if ! npx playwright install chromium --dry-run >/dev/null 2>&1; then
  echo "▶ Installing Playwright Chromium…"
  npx playwright install chromium
fi

PW=(npx playwright test)
[[ "${HEADED}" -eq 1 ]] && PW+=(--headed)
[[ -n "${GREP}" ]]     && PW+=(--grep "${GREP}")
[[ ${#EXTRA_ARGS[@]} -gt 0 ]] && PW+=("${EXTRA_ARGS[@]}")

echo "▶ Running: ${PW[*]}"
echo "──────────────────────────────────────────────────────────────────────"
# Not exec: let the EXIT trap tear the tunnel down afterwards.
status=0
"${PW[@]}" || status=$?
exit "${status}"

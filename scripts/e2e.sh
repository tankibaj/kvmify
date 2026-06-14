#!/usr/bin/env bash
#
# e2e.sh — run KVMify's Playwright UI E2E tests for every workflow.
#
# Pure browser tests: they drive the deployed UI and create/clean up their own
# throwaway resources THROUGH THE UI/API (prefix `kvmify-e2e-`). No virsh, no SSH
# — so this runs the same way from your Mac or from the KVM host.
#
#   • Headless by default.
#   • --headed shows the browser (use on a machine with a display, e.g. your Mac;
#     the host is headless so --headed is ignored there).
#   • Production VMs are never touched (see ⛔ PRODUCTION SAFETY in CLAUDE.md).
#
# Usage:
#   scripts/e2e.sh [options] [-- <extra playwright args>]
#
# Options:
#   --headed            Run with a visible browser (requires a display).
#   --base-url <url>    UI to test (default: $PLAYWRIGHT_BASE_URL or
#                       http://192.168.178.101 — reachable from Mac and host).
#   --grep <pattern>    Only run tests whose title matches <pattern>.
#   -h, --help          Show this help.
#
# Examples:
#   scripts/e2e.sh                      # every workflow, headless
#   scripts/e2e.sh --headed             # watch it in a browser (from your Mac)
#   scripts/e2e.sh --grep "VM workflows"
#   scripts/e2e.sh -- e2e/pools-workflows.spec.js   # one spec file
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_UI_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)/web-ui"

BASE_URL="${PLAYWRIGHT_BASE_URL:-http://192.168.178.101}"
HEADED=0
GREP=""
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --headed)     HEADED=1; shift ;;
    --base-url)   BASE_URL="$2"; shift 2 ;;
    --grep)       GREP="$2"; shift 2 ;;
    -h|--help)    sed -n '2,28p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    --)           shift; EXTRA_ARGS+=("$@"); break ;;
    *)            EXTRA_ARGS+=("$1"); shift ;;
  esac
done

export PLAYWRIGHT_BASE_URL="${BASE_URL}"

# A headed run needs a display; the KVM host has none.
if [[ "${HEADED}" -eq 1 && -z "${DISPLAY:-}" && "$(uname)" != "Darwin" ]]; then
  echo "⚠ --headed requested but no display detected — forcing headless." >&2
  HEADED=0
fi

echo "▶ Target UI: ${BASE_URL}"
if ! curl -fsS -o /dev/null --max-time 8 "${BASE_URL}" 2>/dev/null; then
  echo "  ✖ UI not reachable at ${BASE_URL}. Is KVMify deployed and running?" >&2
  echo "    Override with --base-url <url> if it lives elsewhere." >&2
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
exec "${PW[@]}"

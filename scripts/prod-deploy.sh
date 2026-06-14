#!/usr/bin/env bash
#
# prod-deploy.sh — PRODUCTION deploy: git pull on the host, run the test gates,
# build the frontend, restart the backend, then run E2E against the deployed
# UI. Use when a feature is committed and pushed to GitHub.
#
# The host checkout at /home/naim/kvmify is a clone of the repo (origin).
# Any failing gate (pytest, vitest, playwright) aborts the deploy (set -e).
#
# Usage (from repo root): ./scripts/prod-deploy.sh [branch]   # default: main

set -euo pipefail

HOST="naim@192.168.178.101"
REMOTE="/home/naim/kvmify"
URL="http://192.168.178.101"
BRANCH="${1:-main}"

echo "==> [1/6] Host git fetch + checkout '$BRANCH' + pull"
ssh "$HOST" "cd $REMOTE && git fetch origin && git checkout $BRANCH && git pull --ff-only origin $BRANCH"
ssh "$HOST" "sudo install -m 755 $REMOTE/scripts/sync-base-images.sh /usr/local/bin/sync-base-images.sh && \
             sudo install -m 755 $REMOTE/scripts/provision-vm.sh /usr/local/bin/provision-vm.sh && \
             sudo install -m 755 $REMOTE/scripts/download-base-image.sh /usr/local/bin/download-base-image.sh"

echo "==> [2/6] Backend: install deps + pytest"
ssh "$HOST" "cd $REMOTE/api && ./venv/bin/pip install -q -r requirements.txt && ./venv/bin/python -m pytest -q"

echo "==> [3/6] Frontend: install deps + vitest + build"
ssh "$HOST" "cd $REMOTE/web-ui && npm install --no-audit --no-fund && npx vitest run && npm run build"

echo "==> [4/6] Deploy build + restart backend"
ssh "$HOST" "cp -r $REMOTE/web-ui/dist/* /var/www/kvmify/ && sudo systemctl restart kvmify-api"

echo "==> [5/6] E2E (Playwright) against $URL"
ssh "$HOST" "cd $REMOTE/web-ui && PLAYWRIGHT_BASE_URL=$URL npm run test:e2e"

echo "==> [6/6] Done — deployed '$BRANCH'"
echo "    App:  $URL"
echo "    Docs: $URL/api/docs"

#!/usr/bin/env bash
#
# dev-deploy.sh — DEVELOPMENT deploy: rsync local source → host, run the test
# gates, build the frontend, restart the backend, then run E2E against the
# deployed UI. Use during active feature/bug work for a fast feedback loop.
#
# Any failing gate (pytest, vitest, playwright) aborts the deploy (set -e).
#
# Run from the repo root: ./scripts/dev-deploy.sh

set -euo pipefail

HOST="naim@192.168.178.101"
REMOTE="/home/naim/kvmify"
URL="http://192.168.178.101"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> [1/7] Sync source → host"
rsync -az --delete \
  --exclude __pycache__ --exclude '*.pyc' --exclude venv --exclude '.env' \
  --exclude '*.json' \
  api/ "$HOST:$REMOTE/api/"
rsync -az --delete --exclude node_modules --exclude dist --exclude '.vite' \
  web-ui/ "$HOST:$REMOTE/web-ui/"
rsync -az scripts/ "$HOST:$REMOTE/scripts/"
ssh "$HOST" "sudo install -m 755 $REMOTE/scripts/sync-base-images.sh /usr/local/bin/sync-base-images.sh && \
             sudo install -m 755 $REMOTE/scripts/provision-vm.sh /usr/local/bin/provision-vm.sh && \
             sudo install -m 755 $REMOTE/scripts/download-base-image.sh /usr/local/bin/download-base-image.sh"

echo "==> [2/7] Backend: install deps + pytest"
ssh "$HOST" "cd $REMOTE/api && ./venv/bin/pip install -q -r requirements.txt && ./venv/bin/python -m pytest -q"

echo "==> [3/7] Frontend: install deps + vitest"
ssh "$HOST" "cd $REMOTE/web-ui && npm install --no-audit --no-fund && npx vitest run"

echo "==> [4/7] Frontend: build"
ssh "$HOST" "cd $REMOTE/web-ui && npm run build"

echo "==> [5/7] Deploy build + restart backend"
ssh "$HOST" "cp -r $REMOTE/web-ui/dist/* /var/www/kvmify/ && sudo systemctl restart kvmify-api"

echo "==> [6/7] E2E (Playwright) against $URL"
ssh "$HOST" "cd $REMOTE/web-ui && PLAYWRIGHT_BASE_URL=$URL npm run test:e2e"

echo "==> [7/7] Done"
echo "    App:  $URL"
echo "    Docs: $URL/api/docs"

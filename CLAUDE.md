# KVMify — Claude Code Instructions

## What is KVMify

KVMify is an open source self-service web UI for KVM virtual machine management
on bare metal Ubuntu hosts. It lets you provision, monitor, snapshot, resize,
and console into VMs from a modern premium dark web interface — no Proxmox,
no cloud, no Kubernetes required.

Target user: homelab enthusiasts and self-hosters who run KVM on bare metal
and want a production-grade UI instead of virsh commands or Cockpit.

```
github.com/tankibaj/kvmify
```

---

## Source of Truth

PLAN.md is the single source of truth for:
- Architecture decisions
- Feature scope and UI spec
- API endpoints
- Build order (follow phases and steps exactly)

This file (CLAUDE.md) covers:
- How to access the server
- First task (host discovery)
- Deployment workflow
- Conventions Claude Code must follow

---

## Current Repository State

As of this writing the repo contains only `PLAN.md` and `CLAUDE.md`, no
application code exists yet, and the directory is not yet a git repo. The whole
project is built from scratch. The project is at PLAN.md Phase 1, Step 1.
Future instances should not assume any `api/`, `web-ui/`, or `scripts/`
directory exists locally — build them in PLAN.md's exact phase/step order. Git
and the GitHub repo are created by Claude Code in Phase 1 (see Git & GitHub).

The entire architecture (request flow, API contract, provisioning pipeline, UI
spec, design tokens) lives in PLAN.md. Read it before writing any code. The
runtime is a single bare-metal Ubuntu host where Nginx (:80) fronts a FastAPI
backend (:8000, direct `qemu:///system` libvirt socket) and a noVNC/websockify
proxy (:6080), serving a static React build from `/var/www/kvmify/`.

---

## Common Commands

These become valid only after the relevant PLAN.md phase scaffolds them. All
KVM/build/deploy commands run **on the host** (`naim@192.168.178.101`), not
locally.

```bash
# Deploy (run from local repo root)
./scripts/dev-deploy.sh          # rsync local → host, build, restart kvmify-api
./scripts/prod-deploy.sh [branch] # git pull on host, build, restart (default: main)

# Backend (on host, in api/)
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload   # dev run
sudo systemctl restart kvmify-api                        # restart service
sudo journalctl -u kvmify-api -f                         # tail logs
# API docs for debugging: http://192.168.178.101/api/docs

# Frontend (on host, in web-ui/)
npm install
npm run build
sudo cp -r dist/* /var/www/kvmify/

# Base images
sudo /usr/local/bin/sync-base-images.sh   # checksum-based sync of Ubuntu bases

# Tests (see Testing section)
cd api && source venv/bin/activate && pytest   # backend
cd web-ui && npm test                          # frontend unit/component
cd web-ui && npm run test:e2e                   # Playwright E2E
```

Automated tests gate every phase (see Testing). Beyond unit/integration tests,
backend contracts are also inspectable via the FastAPI `/docs` UI (Phase 2,
Step 14), and final acceptance is a manual provision → console → snapshot →
network flow (Phase 4, Step 32).

---

## Server

- Host: `naim@192.168.178.101`
- Always SSH for any KVM/libvirt/host commands
- Use `sudo` where required
- User `naim` is a sudoer

---

## FIRST TASK (run before writing any code)

SSH into the KVM host and explore the current setup:

```bash
ssh naim@192.168.178.101
```

Run all discovery commands below, then produce a summary report with:
1. What is already in place (KVM, libvirt, networks, storage, services)
2. What needs to be installed or configured before starting
3. Any conflicts or surprises (unexpected networks, pools, existing VMs)
4. Confirm or update PLAN.md assumptions based on findings
5. Only then proceed with PLAN.md Phase 1 Step 1

### Discovery commands

```bash
# OS + kernel
uname -a && lsb_release -a

# KVM + libvirt
virsh version
virsh list --all
virsh nodeinfo

# Networks
virsh net-list --all
ip link show
ip addr show
brctl show 2>/dev/null || bridge link show

# Storage
virsh pool-list --all
ls -lah /var/lib/libvirt/images/ 2>/dev/null
ls -lah /var/lib/libvirt/images/base/ 2>/dev/null
lsblk
df -h

# LVM
sudo vgs 2>/dev/null
sudo lvs 2>/dev/null

# Running services
systemctl status libvirtd
systemctl status nginx 2>/dev/null
systemctl status cockpit 2>/dev/null

# Software versions
python3 --version
node --version 2>/dev/null
npm --version 2>/dev/null
nginx -v 2>/dev/null

# Existing VMs detail
for vm in $(virsh list --all --name); do
  echo "=== $vm ==="
  virsh dominfo $vm
  virsh domifaddr $vm 2>/dev/null
  virsh dumpxml $vm | grep -E "(network|bridge|mac address)"
done
```

---

## Project Location (on host)

```
/home/naim/kvmify/                    # project root (git repo on host)
/home/naim/kvmify/api/                # FastAPI backend
/home/naim/kvmify/web-ui/           # React app source
/home/naim/kvmify/scripts/            # host scripts
/var/lib/libvirt/images/base/   # base images (read-only)
/var/lib/libvirt/images/vms/    # VM disks
/var/www/kvmify/                # React static build (served by Nginx)
/usr/local/bin/                 # sync-base-images.sh
```

---

## Deployment Workflow

Two modes. Claude Code must create both scripts at `scripts/dev-deploy.sh`
and `scripts/prod-deploy.sh` during Phase 4 of PLAN.md.

### Mode 1 — Development (rsync local → host)

Use during active feature/bug work. Rsync source, build on host, restart service.

```
rsync api/ + web-ui/ → host
npm run build on host
cp dist/* → /var/www/kvmify/
systemctl restart kvmify-api
```

### Mode 2 — Production (git push → pull on host)

Use when feature is complete and pushed to GitHub.

```
git push origin main (local)
    ↓
git pull on host
npm run build on host
cp dist/* → /var/www/kvmify/
systemctl restart kvmify-api
```

### Full workflow

```
dev work locally
    → ./scripts/dev-deploy.sh        # test on host
    → git commit + push
    → ./scripts/prod-deploy.sh       # deploy from git
```

---

## Conventions

- Build the project from scratch — no code exists yet; scaffold every file
- Follow PLAN.md build order exactly, phase by phase
- Confirm each phase works before moving to next
- Never skip steps
- All paths: /home/naim/kvmify/ (never /opt/kvmify/)
- Systemd service name: `kvmify-api`
- Nginx config: `/etc/nginx/sites-available/kvmify`
- React app title: KVMify
- No Docker anywhere
- No authentication (LAN only)
- FastAPI /docs must always be accessible for debugging
- Every backend and frontend feature ships with automated tests (see Testing)
- Verify every FE feature/bug via the Playwright MCP server, then capture it as
  a Playwright E2E spec

---

## Git & GitHub

Claude Code is responsible for creating and managing version control — it is not
pre-existing. At the start of Phase 1:

- `git init` the local repo at the project root and make an initial commit
- Create the GitHub repo `tankibaj/kvmify` via the `gh` CLI
  (`gh repo create tankibaj/kvmify --public --source=. --remote=origin --push`)
- Add a `.gitignore` covering `venv/`, `__pycache__/`, `*.pyc`, `node_modules/`,
  `dist/`, `.env`, and `*.qcow2`/`*.img` (never commit VM disks or base images)
- Default branch: `main`. Commit per completed PLAN.md step with clear messages
- The host checkout at `/home/naim/kvmify/` is a clone used by `prod-deploy.sh`

---

## Testing

Both backend and frontend require an automated test suite, written alongside the
feature code in the same step (not deferred).

- **Backend (FastAPI):** `pytest` + `httpx` against the ASGI app. Mock libvirt /
  subprocess / filesystem so tests run without a real KVM host. Cover routers
  (request/response contracts, validation, error paths) and services (provision
  pipeline, cloud-init rendering, subnet-mask→prefix conversion).
  Run: `cd api && source venv/bin/activate && pytest`
- **Frontend (React):** Vitest + React Testing Library. Cover the reusable
  `NetworkConfig` component, form validation, and API-client behavior (mock
  fetch / React Query). Run: `cd web-ui && npm test`
- **E2E (Playwright):** automated end-to-end specs covering the real user
  flows against the deployed UI — dashboard load, provision form (bridge +
  DHCP, bridge + static), VM lifecycle actions, snapshots, network update,
  images sync. Live in `web-ui/e2e/`. Run: `cd web-ui && npm run test:e2e`
- A phase is not "confirmed working" until its tests pass
- `dev-deploy.sh` / `prod-deploy.sh` run pytest + Vitest before building, then
  Playwright E2E against the deployed UI after restart (any failure aborts)

### Verifying frontend work (Playwright MCP)

Every frontend feature or bug fix must be verified interactively through the
**Playwright MCP server** before it is considered done — drive the running app
in a real browser (navigate, fill forms, click actions, read back the DOM and
console) against `http://192.168.178.101` (or the local dev server). Use this
to reproduce bugs, confirm fixes, and check UI states the unit tests can't.
Once a flow is verified manually via the MCP server, capture it as a permanent
Playwright E2E spec in `web-ui/e2e/` so it is covered by the automated suite.

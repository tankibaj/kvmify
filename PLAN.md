# KVMify — Full Build Plan for Claude Code

## What is KVMify

KVMify is an open source self-service web UI for KVM virtual machine management
on bare metal Ubuntu hosts.

**The problem it solves:**
Managing KVM VMs today means memorising virsh commands or using Cockpit which
looks like a 2019 enterprise dashboard. There is no modern, premium, self-hosted
UI for bare metal KVM that just works.

**What KVMify provides:**
- Provision VMs on demand from pre-built Ubuntu base images (no download wait)
- Full VM lifecycle: start, stop, restart, delete, resize, snapshot
- In-browser VNC console (no SSH tunnel, no client install)
- Network control: bridge, NAT, macvtap + DHCP or static IP
- Base image registry with auto-sync and checksum validation
- Premium dark UI — looks like a product, not a sysadmin tool

**Who it is for:**
Homelab enthusiasts and self-hosters running KVM on bare metal Ubuntu who want
a production-grade UI without Proxmox, cloud, or Kubernetes overhead.

**Open source:**
```
github.com/tankibaj/kvmify
```

---

## Host Reality Overrides (added Phase 1 preflight — AUTHORITATIVE)

Host discovery on `naim@192.168.178.101` (Ubuntu 22.04.5, libvirt 8.0.0,
QEMU 6.2.0, Python 3.10.12) found facts that supersede the assumptions written
later in this document. Where they conflict, **these win**:

1. **Storage paths & pools.** `/var/lib/libvirt/images/{base,vms}` do NOT exist.
   Storage is managed as first-class **libvirt storage pools** (see the Storage
   Pools section), not hardcoded paths:
   - Base images → fixed, pool-independent dir `/mnt/nvme1/kvm/pool/base/`
     (read-only bases; not affected by which pool is default).
   - VM disks → created in the **selected storage pool** at provision time,
     defaulting to the KVMify *default pool* when the user doesn't choose one.
   - Seed pool: libvirt pool `default` = dir pool at `/mnt/nvme1/kvm/pool`
     (~486 GB free) is the initial default pool.
2. **libvirt URI.** Backend must open `qemu:///system` EXPLICITLY (shell default
   is `qemu:///session`, which is empty). Confirm `naim` ∈ `libvirt` group.
3. **Network names** (libvirt net name → UI label → virt-install flag):
   - `public`  → "Bridge (LAN)" [default] → `--network bridge=br0`
   - `default` → "NAT (host-only)"        → `--network network=default`
   - macvtap   → "Macvtap (LAN)"          → `--network type=direct,source=<nic>,source_mode=bridge`
   (A `private` NAT net on virbr1/10.0.0.0/24 also exists but is not surfaced.)
4. **VM scope.** KVMify (the product) manages ALL VMs on the host — including 5
   pre-existing ones (`ip-172-16-100-{71,72,73}`, `sandbox`, `container`). No
   namespacing or read-only protection in the app; an end user's lifecycle
   actions act on them too. **BUT this is a runtime product capability, not a
   licence for Claude Code: during development/testing/verification the 5
   production VMs are strictly off-limits to mutation — see "⛔ Production
   Safety" below.**
5. **To install in Step 2** (absent on host): Node.js, npm, nginx, gh CLI,
   noVNC, websockify.

---

## ⛔ Production Safety (AUTHORITATIVE — overrides convenience everywhere)

The host runs **real production VMs** (`ip-172-16-100-{71,72,73}`, `sandbox`,
`container`, and any others). Although KVMify manages all of them, **no
development, test, verification, or maintenance step may ever mutate, modify,
restart, stop, snapshot, restore, resize, re-network, or delete a pre-existing /
production resource** (VM, disk volume, snapshot, network, or storage pool).

**Always CREATE a new, throwaway resource before any UPDATE / DELETE / modify.**

- Verify destructive/mutating behavior only on a throwaway resource you create
  (e.g. a `kvmify-e2e-*` / `kvmify-smoke-*` volume-backed domain, or a temp
  pool/volume), then tear it down fully (`snapshot-delete` → `undefine
  --snapshots-metadata` → `vol-delete`).
- Production VMs are **read-only** for Claude Code: `GET` endpoints and
  `virsh dumpxml/list/dominfo` only. Never invoke a mutating
  endpoint/`virsh`/script against them — not even to "just check".
- Automated unit/integration tests mock libvirt/subprocess/fs (never hit the
  host). Playwright E2E that exercises a mutating flow must create and destroy
  its own throwaway fixture VM (prefix `kvmify-e2e-`); E2E that touches an
  existing VM stays strictly read-only (open UI, then Cancel — never submit).
- Throwaway resources use a greppable disposable prefix (`kvmify-e2e-`,
  `kvmify-smoke-`).

This is the create-before-modify guarantee: the 5 production VMs must remain
byte-for-byte untouched by any KVMify development or test activity.

---

## Context
- Personal homelab, single user, LAN only
- KVM + libvirt already installed on physical Ubuntu host
- Backend + Frontend both run directly on the physical KVM host (no Docker)
- No authentication required
- Premium, modern, production-grade dark UI

---

## Final Architecture

```
Physical Ubuntu KVM Host
│
├── KVM + libvirt + QEMU          (bare metal, already installed)
├── /var/lib/libvirt/images/      (base images + VM disks)
├── /usr/local/bin/               (sync + provision scripts)
│
├── FastAPI Backend               (systemd service, port 8000)
│   └── direct libvirt Unix socket access (qemu:///system)
│   └── direct access to /var/lib/libvirt/images/
│
├── noVNC                         (systemd service, port 6080)
│   └── websocket proxy → VM VNC ports (5900+)
│
└── Nginx                         (port 80)
    ├── / → serves React static build (/var/www/kvmify/)
    ├── /api/ → proxy to FastAPI :8000
    └── /novnc/ → proxy to noVNC :6080
```

---

## Tech Stack

### Backend
- Python 3.12+
- FastAPI (latest)
- uvicorn (ASGI server)
- libvirt-python (direct KVM access)
- Jinja2 (cloud-init templating)
- systemd service
- pytest + httpx (automated tests; libvirt/subprocess/fs mocked)

### Frontend
- React 18 (latest)
- Vite (latest)
- Tailwind CSS v4 (latest)
- Shadcn/ui components
- Lucide React icons
- Recharts (CPU/RAM sparklines)
- @novnc/novnc (in-browser VNC console)
- React Query (data fetching + auto-refresh polling)
- Vitest + React Testing Library (component/unit tests)
- Playwright (E2E tests; FE features/bugs also verified via Playwright MCP server)

### Infrastructure
- Nginx (reverse proxy + static file server)
- noVNC (websocket VNC proxy)
- systemd (process management)
- cloud-image-utils (cloud-localds for cloud-init seed ISO)

---

## Project Folder Structure (on host)

```
/home/naim/kvmify/
├── PLAN.md
├── CLAUDE.md
│
├── api/                              # FastAPI backend
│   ├── main.py
│   ├── requirements.txt
│   ├── routers/
│   │   ├── images.py
│   │   ├── vms.py
│   │   ├── snapshots.py            # gains POST /{snap}/export in Phase 5
│   │   ├── networks.py
│   │   ├── pools.py
│   │   ├── console.py
│   │   └── templates.py            # Phase 5: GET /templates, DELETE /templates/{name}
│   ├── services/
│   │   ├── libvirt_service.py
│   │   ├── cloudinit_service.py
│   │   ├── network_service.py
│   │   ├── pool_service.py
│   │   ├── settings_service.py     # persists default_pool to kvmify-settings.json
│   │   │                           # Phase 5: gains TEMPLATES_DIR + EXPORT_SCRIPT config keys
│   │   ├── snapshot_service.py
│   │   └── template_service.py     # Phase 5: export, list, delete templates
│   └── templates/
│       ├── user-data.yaml.j2
│       └── network-config.yaml.j2
│
├── web-ui/                         # React app
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css
│       ├── api/
│       │   └── client.js             # React Query API calls
│       ├── pages/
│       │   ├── Dashboard.jsx
│       │   ├── Provision.jsx
│       │   ├── VMDetail.jsx
│       │   ├── Pools.jsx
│       │   └── Images.jsx
│       └── components/
│           ├── layout/
│           │   ├── Sidebar.jsx
│           │   └── TopBar.jsx
│           ├── vm/
│           │   ├── VMTable.jsx
│           │   ├── VMActions.jsx
│           │   ├── VMConsole.jsx     # noVNC embed
│           │   └── VMStats.jsx       # Recharts sparklines
│           ├── provision/
│           │   ├── ProvisionForm.jsx
│           │   └── NetworkConfig.jsx  # network + IP section (reused in provision + VM detail)
│           ├── snapshots/
│           │   └── SnapshotList.jsx
│           └── notifications/
│               └── NotificationToast.jsx
│
└── scripts/
    ├── sync-base-images.sh
    ├── provision-vm.sh
    └── export-vm-snapshot.sh       # Phase 5: privileged qemu-img convert helper (installed to /usr/local/bin/)
```

---

## UI Design System

### Aesthetic
- Dark theme
  - Background: #0a0a0f
  - Surface: #111118
  - Border: #1e1e2e
- Accent colors
  - Primary: electric indigo #6366f1
  - Success: emerald #10b981
  - Danger: rose #f43f5e
  - Warning: amber #f59e0b
- Typography
  - UI: Inter (Google Fonts)
  - Monospace (IPs, SSH commands, terminal): JetBrains Mono
- Radius: 12px cards, 8px buttons
- Shadows: subtle indigo glow on hover (rgba(99,102,241,0.2))
- Transitions: 150ms ease on all interactive elements
- Tailwind CSS v4 — use new @theme directive for design tokens

### Tailwind v4 Setup Note
```css
/* src/index.css */
@import "tailwindcss";

@theme {
  --color-background: #0a0a0f;
  --color-surface: #111118;
  --color-border: #1e1e2e;
  --color-primary: #6366f1;
  --color-success: #10b981;
  --color-danger: #f43f5e;
  --color-warning: #f59e0b;
  --font-sans: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  --radius-card: 12px;
  --radius-btn: 8px;
}
```

---

## Pages and Functionality

### 1. Dashboard (/)
**Layout:** fixed sidebar left (240px), scrollable main content right

**Sidebar:**
- Logo + "KVMify" wordmark
- Nav links: Dashboard, Images, Pools, Provision
- Bottom section: live host stats
  - CPU usage %
  - RAM usage %
  - Disk usage %
  - Refreshed every 10s via /api/host/stats

**Main content:**
- Page header: "Virtual Machines" + "New VM" button (links to /provision)
- Stats bar (4 cards): Total VMs / Running / Stopped / Total RAM allocated
- VM Table:
  - Name
  - Ubuntu version (colored badge)
  - Status (animated dot: green=running, grey=stopped, amber=provisioning)
  - IP Address (JetBrains Mono, click-to-copy)
  - CPU / RAM / Disk
  - Uptime
  - Actions dropdown (Start, Stop, Restart, Console, Snapshots, Resize, Delete)
- Polling: React Query refetchInterval every 5s
- Toast notifications: top-right, auto-dismiss 4s

---

### 2. Provision Page (/provision)
**Form fields:**

**Section: General**
- VM Name — text input, validated: lowercase, hyphens only, max 32 chars
- **Image Source** — selector with two options (Phase 5):
  - ◉ **Ubuntu Base Image** (default) — shows the Ubuntu Version dropdown below
  - ○ **From Template** — hides Ubuntu Version; shows a Template dropdown populated from `GET /api/templates` (displays template name + source info; empty state: "No templates available — export a snapshot first")
- Ubuntu Version — dropdown (hidden when "From Template" is selected)
  - Ubuntu 20.04 LTS (Focal)
  - Ubuntu 22.04 LTS (Jammy)
  - Ubuntu 24.04 LTS (Noble)

**Section: Resources**
- CPU — slider: 1 / 2 / 4 / 8 vCPUs
- RAM — slider: 512MB / 1GB / 2GB / 4GB / 8GB
- Disk — slider: 10GB / 20GB / 50GB / 100GB
- Storage Pool — dropdown (populated via GET /pools)
  - Default pool pre-selected (badge: "Default"); shows free space per pool
  - Disk slider max is clamped to the selected pool's available space

**Section: Network**
- Network Interface — dropdown (populated via GET /api/networks)
  - br0 — Bridge (LAN) ← default, already configured on host
  - default — NAT (host-only)
  - macvtap — Macvtap (LAN, no bridge needed)
- IP Assignment — radio
  - ◉ DHCP (auto-assign)
  - ○ Static IP
- [shown only when Static IP selected]
  - IP Address — text input (e.g. 192.168.1.100)
  - Subnet Mask — text input (default: 255.255.255.0)
  - Gateway — text input (e.g. 192.168.1.1)
  - DNS — text input (default: 8.8.8.8)
  - Inline validation: IP format check, conflicts with existing VMs

**Section: Access**
- SSH Public Key — textarea with paste-from-clipboard button

**Resource summary card** (live, updates as form changes):
```
VM Name:     my-vm
OS:          Ubuntu 24.04 LTS
CPU:         2 vCPUs
RAM:         2 GB
Disk:        20 GB
Pool:        default (/mnt/nvme1/kvm/pool)
Network:     br0 (Bridge)
IP:          DHCP  |  or  192.168.1.100 (Static)
```

**Submit flow — progress steps UI:**
```
[✓] Cloning base image
[✓] Generating cloud-init config
[✓] Configuring network
[✓] Starting VM
[~] Waiting for IP...
[ ] Ready
```
On completion: show IP address + copyable SSH command:
```
ssh ubuntu@192.168.x.x
```

---

### 3. VM Detail Page (/vms/:name)
**Tabs:**

**Overview tab:**
- VM metadata: name, OS, status, IP, created date
- Resource allocation: CPU, RAM, disk
- Network info: interface, mode (Bridge/NAT/Macvtap), IP assignment (DHCP/Static)
- Live sparkline charts (Recharts, last 60 data points, 1s interval):
  - CPU usage %
  - RAM usage %
- SSH connection string with copy button
- Quick action buttons: Start / Stop / Restart / Delete

**Console tab:**
- Embedded noVNC viewer (full in-browser VNC console to VM)
- Fetches VNC port from GET /api/vms/{name}/console
- noVNC connects via WebSocket through Nginx → noVNC proxy → VM VNC port
- Toolbar:
  - Send Ctrl+Alt+Del
  - Toggle fullscreen
  - Clipboard paste
- Connection status indicator (Connecting / Connected / Disconnected)

**Snapshots tab:**
- List: snapshot name, created date, description
- Actions per snapshot: Restore / Delete (with confirmation modal) / **Export**
- "Take Snapshot" button → modal:
  - Name (auto-filled: vm-name-YYYYMMDD-HHmm)
  - Description (optional)
  - Confirm button
- **Export modal** (Phase 5 — triggered by "Export" action on a snapshot row):
  - Title: "Export Snapshot to Template"
  - Template Name field (validated: `^[a-z0-9][a-z0-9\-]{0,63}$`, inline error on invalid)
  - Confirm button → calls `POST /api/vms/{name}/snapshots/{snap}/export`
  - On success: green toast "Template '{name}' created" — modal closes
  - On 409: inline error "A template with that name already exists"

**Network tab:**
- Current network config: interface, mode, IP, MAC address
- Change Network Interface — dropdown (same options as provision form)
- Change IP Assignment — radio: DHCP / Static IP
- [if Static IP] IP / Subnet / Gateway / DNS fields
- Warning banner: "Network changes require VM restart to take effect"
- "Apply Changes" button

**Resize tab:**
- Current values shown
- New value sliders (same as provision form)
- Warning banner: "CPU and RAM resize requires VM to be stopped"
- Disk resize note: "Disk resize is applied online, no stop needed"
- "Apply Changes" button

---

### 4. Storage Pools Page (/pools)
- Table columns: Name / State (active/inactive dot) / Type / Capacity / Used / Available (usage bar) / Autostart / Default badge
- "Create Pool" button → modal: Name + Target Path, validates path, creates dir pool
- Per-row actions dropdown: Set as Default, Start / Stop, Toggle Autostart, Delete
  - Delete shows confirmation modal; blocked with a clear message if pool holds VM disks (offer force only when empty-after-review); the default pool's Delete is disabled
- Live capacity bars (green < 75%, amber < 90%, rose ≥ 90%)
- Polling: React Query refetchInterval (10s)

---

### 5. Images Page (/images)
- Table columns: Ubuntu Version / Codename / Size / Last Updated / Checksum / Status
- Status badge: Up to date (green) / Outdated (amber) / Missing (red)
- "Sync All" button → calls POST /api/images/sync, streams log output in terminal UI
- Per-row "Sync" button for individual version
- Last sync timestamp shown per image

**VM Templates section** (Phase 5 — below the base images table on the same page):
- Section heading: "VM Templates"
- Table columns: Name / Size / Created / Source (displayed as `{source_vm} @ {source_snapshot}`) / Actions
- Actions column: Delete button → confirmation modal ("This may break VMs provisioned from this template. Proceed?") → calls `DELETE /api/templates/{name}` → 204 → row removed + red toast "Template '{name}' deleted"
- Empty state: "No templates yet. Export a snapshot from a VM's Snapshots tab to create one."
- Polling: React Query refetchInterval (30s, templates are infrequently updated)

---

## Notification System

Toast component (top-right, z-50):
- VM started → "{name} is now running" — green
- VM stopped → "{name} stopped" — grey
- VM provisioned → "{name} ready at {ip}" — green
- VM deleted → "{name} deleted" — red
- Snapshot taken → "Snapshot saved for {name}" — green
- Snapshot restored → "{name} restored to {snapshot}" — amber
- Template exported → "Template '{template}' created from {vm} @ {snapshot}" — green
- Template deleted → "Template '{template}' deleted" — red
- Network updated → "{name} network config updated, restart to apply" — amber
- Any API error → error message — red

Stored in React state (useState), not persisted, session only.

---

## Backend API Endpoints

### Host
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /host/stats | CPU %, RAM %, disk % of KVM host |

### Networks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /networks | List available libvirt networks (br0, default, macvtap) |

### Storage Pools
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /pools | List pools: name, state, type, capacity/allocation/available bytes, autostart, target path, is_default |
| POST | /pools | Create + start a dir pool `{ name, path }` (define → build → start → autostart on) |
| DELETE | /pools/{name} | Stop + undefine a pool. Refuse if it contains volumes unless `?force=true`. Never deletes the seed `default` pool. |
| PATCH | /pools/{name} | Lifecycle: `{ action: "start" | "stop" | "refresh", autostart?: bool }` |
| POST | /pools/{name}/default | Mark this pool as the KVMify default provisioning pool (persisted) |

**Default-pool persistence:** KVMify stores its app settings (currently just
`default_pool`) in `/home/naim/kvmify/api/kvmify-settings.json`. On first run it
seeds `default_pool` to the libvirt pool named `default`. The provision endpoint
resolves the target pool as: request `storage_pool` → else `default_pool` setting
→ else pool named `default`. Deleting the current default pool is rejected.

---

## Templates (Snapshot → Template Export)

### Concept and Rationale

KVMify has two independent snapshot primitives. They are intentionally kept separate:

| | Internal Snapshots | Templates |
|---|---|---|
| **What it is** | In-place qcow2 internal snapshot | Standalone flat qcow2 image |
| **Purpose** | Ephemeral rollback ("undo button") | Durable, portable, cloneable artifact |
| **Coupling** | Coupled to the VM's disk — destroyed when the VM/disk is deleted | Independent — survives VM/disk/snapshot deletion |
| **Analogue** | Git stash | Cloud AMI / OS image |
| **Use case** | Quick save before a risky change | Freeze a known-good state; re-provision from it |

The export operation converts an existing internal snapshot into a template. It does **not** modify or remove the source snapshot; both primitives continue to exist independently after the export.

### Storage

Templates live in a **dedicated directory** that is completely separate from the base-image directory so `sync-base-images.sh` never touches them:

```
/mnt/nvme1/kvm/pool/templates/          # KVMIFY_TEMPLATES_DIR
├── my-golden-image.qcow2               # flat standalone image (no backing chain)
├── my-golden-image.json                # sidecar metadata
├── web-server-v2.qcow2
└── web-server-v2.json
```

Configuration:
- Config key: `TEMPLATES_DIR`
- Environment variable: `KVMIFY_TEMPLATES_DIR` (overrides the default)
- Default value: `/mnt/nvme1/kvm/pool/templates`

Each template consists of two files:
- **`<name>.qcow2`** — flat, self-contained image produced by `qemu-img convert` (no backing chain dependency).
- **`<name>.json`** — sidecar metadata:
  ```json
  {
    "name": "my-golden-image",
    "source_vm": "sandbox",
    "source_snapshot": "pre-deploy-20260601",
    "os_variant": "ubuntu22.04",
    "created": "2026-06-01T14:32:00Z"
  }
  ```

**Template name rule:** `^[a-z0-9][a-z0-9\-]{0,63}$` — lowercase alphanumeric and hyphens, 1–64 characters, must start with alphanumeric.

### Export Mechanics

Because `qemu-img convert` requires root when the VM is running (to access the live disk safely), a scoped privileged helper script handles the conversion:

**`scripts/export-vm-snapshot.sh`** (installed to `/usr/local/bin/export-vm-snapshot.sh`)

- Invoked by the backend via `sudo /usr/local/bin/export-vm-snapshot.sh`
- Sudoers grant: `naim ALL=(ALL) NOPASSWD: /usr/local/bin/export-vm-snapshot.sh` (scoped — only this script, not general sudo)
- Runs: `qemu-img convert -U -O qcow2 -s <snapshot> <source_disk> <dest>`
  - `-U` (unsafe mode) allows the export to proceed while the VM is powered on; the snapshot state is immutable so this is safe
  - `-O qcow2` produces a flat, backing-chain-free output image
  - `-s <snapshot>` selects the internal snapshot to flatten
- After conversion, chowns the result to `naim:naim` so subsequent list and delete operations are unprivileged

**Backend responsibilities:**
1. Resolve the source disk path from the domain XML (first `<disk device="disk">` source)
2. Invoke the helper script with `subprocess.run` (checked=True)
3. Write the `.json` sidecar to `TEMPLATES_DIR`
4. Return `TemplateInfo` to the caller

### Provisioning from a Template

`ProvisionRequest` gains two new optional fields (backwards-compatible — existing clients default to `base_image` behaviour):

```python
source_type: Literal["base_image", "template"] = "base_image"
template_name: str | None = None   # required when source_type == "template"
```

When `source_type == "template"`:
- The template `.qcow2` is used as the backing image in place of the Ubuntu base image — `provision-vm.sh` is unchanged; only the path argument changes
- `ubuntu_version` is ignored; `os_variant` is read from the template's `.json` sidecar and passed to `virt-install`
- All other provision fields (CPU, RAM, disk, network, IP, SSH key, storage pool) work identically

**Known caveat (document prominently):** A template used as a backing image for provisioned VMs must persist for as long as those VMs exist. Deleting a template that has been used as a backing image will corrupt those VMs' disks — the same constraint that applies to base images. KVMify does not enforce this at delete time (no reverse index); it is the operator's responsibility.

### Images
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /images | List base images with size, checksum, status |
| POST | /images/sync | Sync all or { version } specific |
| GET | /images/sync/status | Last sync result + timestamp |

### VMs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /vms | List all VMs: status, IP, CPU, RAM, uptime |
| POST | /vms/provision | Provision new VM |
| GET | /vms/{name} | VM detail + live resource stats |
| POST | /vms/{name}/start | Start VM |
| POST | /vms/{name}/stop | Graceful shutdown |
| POST | /vms/{name}/restart | Restart VM |
| DELETE | /vms/{name} | Delete VM + disk cleanup |
| PATCH | /vms/{name}/resize | Resize CPU / RAM / disk |
| PATCH | /vms/{name}/network | Update network interface + IP assignment |
| GET | /vms/{name}/console | Return VNC display port for noVNC |

### Snapshots
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /vms/{name}/snapshots | List snapshots |
| POST | /vms/{name}/snapshots | Take snapshot |
| POST | /vms/{name}/snapshots/{snap}/restore | Restore snapshot |
| DELETE | /vms/{name}/snapshots/{snap} | Delete snapshot |
| POST | /vms/{name}/snapshots/{snap}/export | Export snapshot to a template → 201 `TemplateInfo`. Body: `{ "template_name": str }`. Errors: 404 (VM or snapshot not found), 409 (template name already exists), 400 (invalid name format). |

### Templates
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /templates | List all templates → `TemplateInfo[]` |
| DELETE | /templates/{name} | Delete template — removes `<name>.qcow2` and `<name>.json` → 204. Returns 404 if not found. |

**`TemplateInfo` shape:**
```json
{
  "name": "my-golden-image",
  "size": 2147483648,
  "created": "2026-06-01T14:32:00Z",
  "source_vm": "sandbox",
  "source_snapshot": "pre-deploy-20260601",
  "os_variant": "ubuntu22.04"
}
```
(`size` is in bytes; `created` is ISO-8601 UTC.)

**`ProvisionRequest` additions** (both fields optional; existing clients are unaffected):
```python
source_type: Literal["base_image", "template"] = "base_image"
template_name: str | None = None   # required when source_type == "template"
```

---

## VM Provisioning Flow

```
POST /vms/provision
{ vm_name, ubuntu_version, cpu, ram_mb, disk_gb, ssh_public_key,
  network, ip_mode, static_ip, subnet_mask, gateway, dns,
  storage_pool }   # optional — falls back to the KVMify default pool
    │
    ├── 0. resolve pool: storage_pool → default_pool setting → pool "default";
    │       disk path = <pool target path>/<vm_name>.qcow2
    ├── 1. validate: name unique, base image exists, static IP not in use,
    │       pool exists + active + has capacity for disk_gb
    ├── 2. qemu-img create -f qcow2 -b <base>.img -F qcow2 <pool>/<vm>.qcow2 <disk>G
    ├── 3. render cloud-init user-data.yaml via Jinja2
    ├── 4. if ip_mode == static:
    │       render network-config.yaml (cloud-init v2 format)
    │       cloud-localds seed.iso user-data.yaml --network-config network-config.yaml
    │   else:
    │       cloud-localds seed.iso user-data.yaml
    ├── 5. resolve virt-install --network flag:
    │       bridge  → --network bridge=br0
    │       nat     → --network network=default
    │       macvtap → --network type=direct,source=<nic>,source_mode=bridge
    ├── 6. virt-install --import --noautoconsole --graphics vnc
    ├── 7. poll virsh domifaddr every 3s (timeout 120s)
    └── 8. return { vm_name, ip, status: "running", vnc_port, network, ip_mode }
```

---

## cloud-init Templates

### user-data.yaml.j2
```yaml
#cloud-config
hostname: {{ vm_name }}
users:
  - name: ubuntu
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - {{ ssh_public_key }}
package_update: false
```

### network-config.yaml.j2 (used only for static IP)
```yaml
version: 2
ethernets:
  enp1s0:
    addresses:
      - {{ static_ip }}/{{ prefix_length }}
    gateway4: {{ gateway }}
    nameservers:
      addresses: [{{ dns }}]
```

Note: `prefix_length` converted from subnet mask (e.g. 255.255.255.0 → 24) by backend.

---

## noVNC Setup (on host)

```bash
# Install noVNC
sudo apt install novnc websockify

# systemd service: /etc/systemd/system/novnc.service
[Unit]
Description=noVNC WebSocket Proxy
After=network.target

[Service]
ExecStart=/usr/bin/websockify --web /usr/share/novnc 6080 localhost:5900
Restart=always
User=nobody

[Install]
WantedBy=multi-user.target
```

Note: websockify is launched per-VM dynamically by the backend
when the console tab is opened, targeting the specific VM VNC port.

---

## FastAPI systemd Service

```ini
# /etc/systemd/system/kvmify-api.service
[Unit]
Description=KVMify FastAPI Backend
After=network.target libvirtd.service

[Service]
User=<your-user>
WorkingDirectory=/home/naim/kvmify/api
ExecStart=/home/naim/kvmify/api/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## Nginx Config

```nginx
# /etc/nginx/sites-available/kvmify
server {
    listen 80;
    server_name _;

    # React frontend (static build)
    location / {
        root /var/www/kvmify;
        try_files $uri $uri/ /index.html;
    }

    # FastAPI backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # noVNC WebSocket proxy
    location /novnc/ {
        proxy_pass http://127.0.0.1:6080/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Base Image Registry

```
/var/lib/libvirt/images/base/
├── ubuntu-2004-base.img    # focal  — read-only (chmod 444)
├── ubuntu-2204-base.img    # jammy  — read-only (chmod 444)
└── ubuntu-2404-base.img    # noble  — read-only (chmod 444)

/var/lib/libvirt/images/vms/
├── my-vm.qcow2             # CoW diff only, backed by base image
└── dev-box.qcow2
```

---

## Sync Script (/usr/local/bin/sync-base-images.sh)

Logic:
1. Declare map of versions → cloud image URLs + SHA256SUMS URLs
2. For each version: fetch upstream SHA256, compare with local
3. Download only if changed or missing
4. chmod 444 after download
5. Log result with timestamp

Cron (weekly, Sunday 02:00):
```
0 2 * * 0 root /usr/local/bin/sync-base-images.sh >> /var/log/vm-image-sync.log 2>&1
```

---

## Frontend Deployment

```bash
cd /home/naim/kvmify/web-ui
npm install
npm run build
sudo cp -r dist/* /var/www/kvmify/
```

Redeploy = one command. No container, no registry, no compose.

---

## Build Order for Claude Code

Project is built from scratch — no code exists yet. Tests are written in the
same step as the feature they cover, and a step is not done until its tests pass.

| Phase | Step | Task | Notes |
|-------|------|------|-------|
| 1 | 0 | Init git + create GitHub repo | `git init` locally, `.gitignore`, initial commit, `gh repo create tankibaj/kvmify --public --source=. --remote=origin --push` |
| 1 | 1 | Create directory structure on host | /home/naim/kvmify, /var/lib/libvirt/images/base, /var/www/kvmify |
| 1 | 2 | Install dependencies on host | python3, venv, nginx, novnc, websockify, cloud-image-utils, nodejs |
| 1 | 3 | Write + test sync-base-images.sh | Start with ubuntu-2404 only |
| 1 | 4 | Sync all 3 Ubuntu base images | focal, jammy, noble |
| 2 | 5 | Scaffold FastAPI project + venv | /home/naim/kvmify/api/ |
| 2 | 6 | Backend: networks router | list libvirt networks (br0, default, macvtap) |
| 2 | 6b | Backend: pools router + settings service | list/create/delete/lifecycle pools, default-pool persistence (kvmify-settings.json) |
| 2 | 7 | Backend: images router | list, sync, sync status |
| 2 | 8 | Backend: vms router | provision (with network + IP + **pool resolution**), lifecycle, resize, stats |
| 2 | 9 | Backend: network update endpoint | PATCH /vms/{name}/network |
| 2 | 10 | Backend: snapshots router | list, take, restore, delete |
| 2 | 11 | Backend: console endpoint | VNC port lookup |
| 2 | 12 | Backend: host stats endpoint | CPU, RAM, disk |
| 2 | 13 | systemd service for FastAPI | enable + start |
| 2 | 14 | Backend automated test suite | pytest + httpx, libvirt/subprocess/fs mocked; routers (incl. pools) + services (incl. pool resolution + default-pool persistence); must pass |
| 2 | 14b | Test all endpoints via /docs | manual smoke check before building UI |
| 3 | 15 | Scaffold React 18 + Vite + Tailwind v4 | /home/naim/kvmify/web-ui/ |
| 3 | 16 | Design system setup | @theme tokens, Inter + JetBrains Mono fonts |
| 3 | 17 | Layout: Sidebar + TopBar | dark theme, nav, host stats |
| 3 | 18 | Dashboard: VMTable + stats bar | polling every 5s |
| 3 | 19 | NetworkConfig component | reusable: interface dropdown + DHCP/Static toggle |
| 3 | 20 | Provision page: form + progress steps | sliders, **storage pool dropdown**, network section, SSH key, live summary |
| 3 | 21 | VM Detail: Overview tab + sparklines | Recharts CPU/RAM, network info |
| 3 | 22 | VM Detail: Console tab | noVNC embed via @novnc/novnc |
| 3 | 23 | VM Detail: Snapshots tab | list, take, restore, delete |
| 3 | 24 | VM Detail: Network tab | interface + IP update form |
| 3 | 25 | VM Detail: Resize tab | sliders + warnings |
| 3 | 26 | Images page | table, sync button, log output |
| 3 | 26b | Pools page | table, capacity bars, create modal, lifecycle actions, set-default |
| 3 | 27 | Notification toast system | React state, auto-dismiss (incl. pool create/delete/default events) |
| 3 | 27b | Frontend automated test suite | Vitest + RTL; NetworkConfig, form validation, API client (mocked); must pass |
| 4 | 28 | Nginx config + deploy React build | /var/www/kvmify/ |
| 4 | 28b | Playwright E2E suite + MCP verification | web-ui/e2e/; dashboard, provision (bridge+DHCP, bridge+static, **pool selection**), lifecycle, snapshots, network update, images sync, **pool create/set-default/delete**; verify each flow via Playwright MCP server first |
| 4 | 29 | noVNC + websockify systemd service | port 6080 |
| 4 | 30 | Create scripts/dev-deploy.sh | rsync local → host + build + restart |
| 4 | 31 | Create scripts/prod-deploy.sh | git pull on host + build + restart |
| 4 | 32 | End-to-end test | provision (bridge+static) → console → snapshot → network update |
| 4 | 33 | Weekly cron for image sync | /etc/cron.d/kvmify-image-sync |
| **5** | **34** | **Config + schemas** | Add `TEMPLATES_DIR` + `EXPORT_SCRIPT` to config/settings. Add `TemplateInfo` Pydantic model. Extend `ProvisionRequest` with `source_type` (default `"base_image"`) and `template_name` (optional). |
| 5 | 35 | template_service + disk-path helper + export script | `api/services/template_service.py`: `export_snapshot()` (resolve disk path from domain XML, invoke sudo helper, write `.json` sidecar), `list_templates()`, `delete_template()`. `scripts/export-vm-snapshot.sh`: `qemu-img convert -U -O qcow2 -s <snap> <src> <dest>` + chown. |
| 5 | 36 | templates router + export route + main.py wiring | `api/routers/templates.py`: `GET /templates`, `DELETE /templates/{name}`. Add `POST /vms/{name}/snapshots/{snap}/export` to `api/routers/snapshots.py`. Register both in `main.py`. |
| 5 | 37 | Provision template-source integration | In `libvirt_service.py` / provision flow: when `source_type == "template"`, resolve `template_name` → `.qcow2` path and read `os_variant` from `.json` sidecar; pass as backing image and os_variant to `provision-vm.sh`. No changes to `provision-vm.sh` itself. |
| 5 | 38 | Frontend: client hooks + SnapshotList export modal + Images templates section + ProvisionForm source selector | `api/client.js`: add `exportSnapshot()`, `listTemplates()`, `deleteTemplate()` hooks. `SnapshotList.jsx`: add Export action + export modal (template name input, validation, 409 handling). `Images.jsx`: add VM Templates table section with delete confirmation. `ProvisionForm.jsx`: add Image Source radio (Base Image / From Template) + Template dropdown (populated from `listTemplates`). |
| 5 | 39 | Tests | **pytest** `tests/test_templates.py`: export success, duplicate name (409), missing snapshot (404), invalid name (400), list, delete — libvirt + subprocess + fs mocked. Provision-from-template test: `source_type="template"` resolves sidecar + passes correct backing path. **Vitest**: export modal (open, validation, success, 409), VM Templates section render + delete confirmation, ProvisionForm source selector toggle. **Playwright E2E** (non-destructive): VM Templates section renders on `/images`; export modal opens and cancels on existing `sandbox` VM snapshot; provision source toggle shows/hides Template dropdown. All tests must pass before proceeding. |
| 5 | 40 | Host setup + smoke test | On host: `mkdir -p /mnt/nvme1/kvm/pool/templates`. Install `export-vm-snapshot.sh` to `/usr/local/bin/`, chmod 755. Add sudoers grant: `naim ALL=(ALL) NOPASSWD: /usr/local/bin/export-vm-snapshot.sh`. Run `dev-deploy.sh`. Live smoke test: export a snapshot from `sandbox` → verify template appears in `/images` → provision a new VM from it → confirm VM starts. |

---

## Deployment Scripts

Both scripts live at `/home/naim/kvmify/scripts/` and are created during Phase 4.

### scripts/dev-deploy.sh
Rsync local source → host, build frontend on host, restart backend.
Used during active development for fast feedback loop.

Must:
- rsync `api/` excluding `__pycache__`, `*.pyc`, `venv/`, `.env`
- rsync `web-ui/` excluding `node_modules/`, `dist/`
- rsync `scripts/sync-base-images.sh` → `/usr/local/bin/`
- run `pip install -r requirements.txt` in venv, then `pytest` (abort on failure)
- run `npm install`, then `npm test` (abort on failure), then `npm run build`
- copy `dist/*` → `/var/www/kvmify/`
- restart `kvmify-api` systemd service
- run `npm run test:e2e` (Playwright) against the deployed UI (abort on failure)
- print final URLs on completion

### scripts/prod-deploy.sh
Git pull on host, build, restart. Used when feature is committed and pushed.

Must:
- accept optional branch argument (default: main)
- git fetch + checkout + pull on host
- pip install in venv, then `pytest` (abort on failure)
- run `npm install`, then `npm test` (abort on failure), then `npm run build`
- copy `dist/*` → `/var/www/kvmify/`
- restart `kvmify-api` systemd service
- run `npm run test:e2e` (Playwright) against the deployed UI (abort on failure)
- print final URLs on completion

---

- Both backend and frontend run directly on the KVM host (no Docker)
- FastAPI managed by systemd, direct libvirt Unix socket access
- React 18 + Vite (latest) + Tailwind CSS v4 (latest)
- noVNC + websockify for in-browser VNC console
- Nginx: single entry point, proxies API + noVNC, serves React static build
- qcow2 backing file for fast CoW provisioning (single host)
- Checksum-based image sync, download only on upstream change
- No authentication (LAN only, personal homelab)
- Toast-only notifications, React state, no persistence needed
- FastAPI /docs always available for development + debugging
- Bridge (br0) already configured on host, used as default network
- Three network modes: Bridge (br0), NAT (default), Macvtap
- IP assignment: DHCP or Static, both at provision time and updatable post-creation
- Static IP injected via cloud-init network-config v2 (not DHCP reservation)
- NetworkConfig.jsx is a shared component used in both ProvisionForm and VM Detail Network tab
- Network changes on existing VMs require restart to take effect (shown as warning in UI)

---

## Testing

Tests are written in the same step as the feature they cover. A step is not done until its tests pass. Both deploy scripts (`dev-deploy.sh`, `prod-deploy.sh`) run the full suite and abort on any failure.

### Backend (pytest)

Run: `cd api && source venv/bin/activate && pytest`

- `tests/test_routers.py` — request/response contracts, validation, and error paths for all routers (networks, pools, images, vms, snapshots, console, host stats). Libvirt, subprocess, and filesystem calls are mocked.
- `tests/test_services.py` — provision pipeline (pool resolution, cloud-init rendering, subnet-mask-to-prefix conversion, network-flag resolution), default-pool persistence, network update flow.
- `tests/test_templates.py` *(Phase 5)* — export success (mocked subprocess + fs), duplicate template name → 409, missing snapshot → 404, invalid name format → 400, list (reads `.json` sidecars), delete (removes `.qcow2` + `.json`). Provision-from-template: `source_type="template"` resolves sidecar `os_variant` and passes the template `.qcow2` as the backing image path.

### Frontend (Vitest + React Testing Library)

Run: `cd web-ui && npm test`

- `NetworkConfig` component: interface dropdown, DHCP/Static toggle, static-IP field visibility and validation.
- `ProvisionForm`: form validation (name pattern, required fields, pool disk-size clamping), Image Source selector *(Phase 5)*.
- API client (`api/client.js`): fetch mock coverage for all endpoints including template hooks *(Phase 5)*.
- `SnapshotList` export modal *(Phase 5)*: modal open/close, template name validation, success path, 409 duplicate-name error display.
- VM Templates section on `Images.jsx` *(Phase 5)*: table renders from mocked `GET /templates` response, delete confirmation modal, empty state.
- `ProvisionForm` source selector *(Phase 5)*: toggling "From Template" hides Ubuntu Version, shows Template dropdown.

### E2E (Playwright)

Run: `cd web-ui && npm run test:e2e`

**Coverage rule: every user-facing workflow MUST have an automated Playwright E2E UI test.** No workflow is considered done until a spec drives it end-to-end through the real UI. Each flow is first verified interactively via the Playwright MCP server, then captured as a permanent spec. Mutating workflows run against a throwaway `kvmify-e2e-*` fixture the spec creates and destroys; read-only workflows open the UI and Cancel. New workflows ship with their E2E spec in the same change.

Specs live in `web-ui/e2e/`.

- `dashboard.spec.js` — page loads, VM table renders, polling updates.
- `provision.spec.js` — bridge + DHCP flow, bridge + static-IP flow, pool selection, form validation.
- `lifecycle.spec.js` — start, stop, restart, delete (against `sandbox` VM).
- `snapshots.spec.js` — take snapshot, restore, delete.
- `network.spec.js` — network interface + IP update.
- `images.spec.js` — images table renders, Sync All button, log output stream.
- `pools.spec.js` — pool table, create pool modal, set-default, lifecycle actions.
- `templates.spec.js` *(Phase 5, non-destructive)*:
  - VM Templates section renders on `/images` (empty state or table).
  - Export modal opens and cancels on existing `sandbox` VM snapshot (no actual export committed).
  - Provision form source selector toggles between "Ubuntu Base Image" and "From Template"; Template dropdown appears when "From Template" is selected.

# KVMify E2E Tests

End-to-end UI regression tests for KVMify, written with [Playwright](https://playwright.dev).
They drive the **real deployed app in a real browser** and verify whole user
workflows — the things unit tests (Vitest) and API tests (pytest) can't catch on
their own.

---

## Overview

These specs are **pure browser tests**. They talk to the deployed UI over HTTP
and create / clean up their **own throwaway resources through the UI and public
API** — no `virsh`, no SSH, no host access required. That means the exact same
suite runs from your Mac or from the KVM host; only the target URL differs.

### ⛔ Production safety

The host runs real production VMs (`sandbox`, `container`, `ip-172-16-100-*`).
**The tests never touch them.** Every mutating spec provisions/creates its own
disposable resource (prefixed **`kvmify-e2e-`**), operates only on that, and
deletes it — with an idempotent API cleanup in `beforeAll`/`afterAll` so nothing
is left behind even if a test aborts mid-run. See the ⛔ PRODUCTION SAFETY
sections in `CLAUDE.md` and `PLAN.md`.

### What's covered

| Spec | Type | What it does |
|------|------|--------------|
| `dashboard.spec.js` | read-only | Dashboard loads: header, stat cards, host stats, VM table |
| `navigation.spec.js` | read-only | Sidebar navigates between all pages |
| `provision.spec.js` | read-only | Provision form validation & summary (no submit) |
| `images.spec.js` | read-only | Base-images table + Sync All affordance |
| `templates.spec.js` | read-only | Images "VM Templates" section + Provision image-source toggle |
| `pools.spec.js` | read-only | Pools page + Create Pool modal open/close (no create) |
| **`vm-workflows.spec.js`** | **destructive** | **Provisions a throwaway VM, then exercises every VM workflow on it: detail tabs render → snapshot → export template → restore → delete snapshot → network update → stop → resize → delete template → delete VM** |
| **`pools-workflows.spec.js`** | **destructive** | **Creates a throwaway pool, then stop/start → set-default (restored) → delete** |

The destructive specs are `serial` (each test builds on the last) and create
their resource once at the top.

> **Note on timing:** `vm-workflows.spec.js` actually **provisions a real VM**
> (the central workflow) and waits for it to boot, then later stops it to test
> resize. Expect it to take **~2–4 minutes**. It uses the NAT (`private`)
> network so the IP lease — and therefore provisioning — is fast.

---

## Running

A single wrapper script handles both environments:

```bash
scripts/e2e.sh [options] [-- <extra playwright args>]
```

| Option | Meaning |
|--------|---------|
| `--headed` | Show the browser (needs a display — use on your Mac; ignored on the headless host) |
| `--base-url <url>` | UI to test (default `http://192.168.178.101`, reachable from Mac **and** host) |
| `--grep <pattern>` | Only run tests whose title matches the pattern |
| `-h`, `--help` | Help |

It auto-installs the npm deps and the Playwright Chromium browser on first run,
checks the UI is reachable, then runs the suite.

### From the KVM host (always headless)

```bash
ssh naim@192.168.178.101
cd /home/naim/kvmify
./scripts/e2e.sh --base-url http://127.0.0.1      # all workflows, headless
```

### From a dev machine / Mac

**Recommended: `--tunnel`** — it SSH-forwards the host UI to `127.0.0.1` so the
browser never hits the LAN-access blocks that otherwise cause
`net::ERR_ADDRESS_UNREACHABLE` (macOS "Local Network" permission / Chrome LNA).
This is the verified-working path (full suite green from a Mac):

```bash
cd ~/Repos/kvmify
./scripts/e2e.sh --tunnel              # all workflows, headless — verified working
./scripts/e2e.sh --tunnel --headed     # watch it in a browser
./scripts/e2e.sh --tunnel --grep "VM workflows"
```

Direct (no tunnel) also works **if** your Mac can reach the host in an automated
browser — the config already requests the `local-network-access` permission, but
you may still need to grant the macOS Local Network prompt (see Troubleshooting):

```bash
./scripts/e2e.sh                 # headless, against http://192.168.178.101
./scripts/e2e.sh --headed        # watch it run in a visible browser
```

### Useful examples

```bash
# Just the VM lifecycle workflow
./scripts/e2e.sh --grep "VM workflows"

# Just the storage-pools workflow, headed
./scripts/e2e.sh --headed --grep "pools workflows"

# A single spec file
./scripts/e2e.sh -- e2e/templates.spec.js

# Only the fast read-only specs (skip the slow provisioning ones)
./scripts/e2e.sh --tunnel -- e2e/dashboard.spec.js e2e/navigation.spec.js \
                    e2e/images.spec.js e2e/pools.spec.js \
                    e2e/templates.spec.js e2e/provision.spec.js

# Against a different deployment
./scripts/e2e.sh --base-url http://10.0.0.5
```

### Without the wrapper (raw Playwright)

```bash
cd web-ui
npm install
npx playwright install chromium
PLAYWRIGHT_BASE_URL=http://192.168.178.101 npx playwright test          # headless
PLAYWRIGHT_BASE_URL=http://192.168.178.101 npx playwright test --headed
```

---

## Troubleshooting: `net::ERR_ADDRESS_UNREACHABLE` from a Mac

If `curl http://192.168.178.101` works but the browser tests fail to load the
page (`net::ERR_ADDRESS_UNREACHABLE`), the OS/browser is blocking **local-network
access** for the automated browser.

**Guaranteed fix — `--tunnel`:** forwards the host UI to `127.0.0.1` over SSH, so
the browser hits loopback (never blocked). Works regardless of the cause below:

```bash
scripts/e2e.sh --tunnel            # from your Mac
scripts/e2e.sh --tunnel --headed
```

The two underlying causes (both also handled directly in `playwright.config.js`):

1. **macOS 15 (Sequoia) "Local Network" privacy permission** — macOS blocks an
   app from reaching LAN devices until you grant it. The first run usually pops
   a prompt *"Terminal wants to access devices on your local network"* → click
   **Allow**. If you dismissed it, enable it manually:
   **System Settings → Privacy & Security → Local Network →** toggle on your
   terminal (Terminal / iTerm) and/or `node`. This is enforced by macOS and no
   browser flag can bypass it.

2. **Chrome 142+ Local Network Access (LNA)** — Chromium treats LAN IPs as
   non-public and, with no human to approve the prompt, denies them. The
   Playwright config already handles this with
   `use.permissions: ['local-network-access']` (the supported fix, Playwright
   ≥1.5x) plus `--ip-address-space-overrides=<host>:80=public` and
   `--disable-features=LocalNetworkAccessChecks,…` launch args.

Running **on the KVM host itself** also avoids both (the target is `127.0.0.1`).
If the direct LAN run still fails after granting the macOS permission, use
`--tunnel` — it always works.

## Reports & debugging

- Failures write traces, screenshots, and a `error-context.md` page snapshot to
  `web-ui/test-results/`.
- Open the HTML report: `cd web-ui && npx playwright show-report`.
- Run one test with the inspector: `npx playwright test --debug -- e2e/vm-workflows.spec.js`.

---

## Conventions for new specs

- **Never reference a production VM/pool.** Create your own `kvmify-e2e-*`
  resource through the UI, and clean it up via the public API
  (`request.newContext({ baseURL }).delete('/api/...')`) in `beforeAll` **and**
  `afterAll` so re-runs are idempotent.
- Mutating flows belong in a `test.describe.serial(...)` block.
- Prefer role/text locators; modals portal to the end of `<body>`, so when a
  button label appears both on the page and in an open modal, use `.last()` for
  the modal's copy and `.first()` for the page's.
- Deep-link VM tabs with `/vms/<name>?tab=snapshots|network|resize|console` to
  avoid tab-click flakiness.
- VM state text is lowercase in the DOM (`running`, `shutoff`); the UI only
  capitalises it visually via CSS.

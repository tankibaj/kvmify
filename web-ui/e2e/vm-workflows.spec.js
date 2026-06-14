import { test, expect, request } from '@playwright/test'

// End-to-end VM workflows — PURE BROWSER. No virsh, no SSH.
//
// This spec provisions its OWN throwaway VM through the Provision UI, then
// exercises every VM workflow on it through the UI, and deletes it. Cleanup
// uses the public HTTP API (the same call the UI makes), so the whole spec runs
// from a plain browser against the deployed app — locally or on the host.
//
// ⛔ PRODUCTION SAFETY: only ever touches resources it creates (prefix
// `kvmify-e2e-`). The 5 production VMs are never referenced.

const VM   = 'kvmify-e2e-vm'
const TPL  = 'kvmify-e2e-tpl'
const SNAP = 'e2e-snap'
// Second throwaway VM, provisioned FROM the exported template — the regression
// for "Export template → Provision a new, independent VM from it".
const VM2  = 'kvmify-e2e-vm-from-tpl'
// Dummy key — backend stores it verbatim into cloud-init; format isn't validated.
const SSH_KEY =
  'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIE2eRegressionDummyKeyDoNotUseAnywhere e2e@kvmify'

const BASE = process.env.PLAYWRIGHT_BASE_URL || 'http://192.168.178.101'

// Best-effort teardown via the public API (idempotent; ignores 404s).
async function cleanup() {
  const ctx = await request.newContext({ baseURL: BASE })
  // Delete both VMs before the template: a template-provisioned VM uses the
  // template qcow2 as its disk's backing file, so the template must go last.
  await ctx.delete(`/api/vms/${VM}`).catch(() => {})
  await ctx.delete(`/api/vms/${VM2}`).catch(() => {})
  await ctx.delete(`/api/templates/${TPL}`).catch(() => {})
  await ctx.dispose()
}

test.describe.serial('VM workflows (self-provisioned throwaway VM, never production)', () => {
  test.beforeAll(async () => { await cleanup() })  // clear leftovers from a prior aborted run
  test.afterAll(async () => { await cleanup() })

  // 1 ── Provision a VM through the Provision UI (NAT network = fast IP lease).
  test('provision a new VM via the Provision form', async ({ page }) => {
    test.setTimeout(240_000)

    await page.goto('/provision')
    await page.getByLabel('VM Name').fill(VM)
    await page.locator('#ssh-public-key').fill(SSH_KEY)
    // Pick the NAT network ('private') so the IP lease is fast (bridge waits ~120s).
    await page.locator('select#network').selectOption('private')

    await page.getByRole('button', { name: 'Provision VM' }).click()

    // Provisioning runs the full pipeline (clone → cloud-init → virt-install →
    // IP poll). Wait for the success panel.
    await expect(page.getByText('VM Ready!')).toBeVisible({ timeout: 220_000 })
    await expect(page.getByText('[object Object]')).toHaveCount(0)
  })

  // 2 ── The new VM appears in the VM list (the Dashboard at "/").
  test('provisioned VM appears in the dashboard VM list', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText(VM, { exact: true }).first()).toBeVisible({ timeout: 20_000 })
  })

  // 2b ── VM detail page renders all tabs (read-only smoke; our own VM).
  test('VM detail page renders all tabs', async ({ page }) => {
    await page.goto(`/vms/${VM}`)
    for (const tab of ['Overview', 'Console', 'Snapshots', 'Network', 'Resize']) {
      await expect(
        page.getByRole('button', { name: tab, exact: true }).first()
      ).toBeVisible({ timeout: 15_000 })
    }
    await expect(page.getByText('[object Object]')).toHaveCount(0)
  })

  // 2c ── Toggle the VM's autostart flag on, then off, through the UI. Placed
  //       right after the first provision (the only reliably-fast step) and
  //       BEFORE the heavier snapshot/template/stop steps, so their VM-timing
  //       flakiness can never mask this regression. Autostart is state-independent.
  test('toggle VM autostart on and off', async ({ page }) => {
    test.setTimeout(40_000)
    await page.goto(`/vms/${VM}`)  // Overview tab — Identity card has the toggle
    await expect(page.getByTitle(/Autostart (disabled|enabled)/)).toBeVisible({ timeout: 15_000 })

    // Enable
    await page.getByTitle(/Autostart disabled/).click()
    await expect(page.getByText(new RegExp(`Autostart enabled for ${VM}`))).toBeVisible({ timeout: 15_000 })

    // Disable again (restore original state before the rest of the workflow)
    await page.getByTitle(/Autostart enabled/).click()
    await expect(page.getByText(new RegExp(`Autostart disabled for ${VM}`))).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText('[object Object]')).toHaveCount(0)
  })

  // 3 ── Take a snapshot of the (running) VM through the UI.
  test('take a snapshot of the running VM', async ({ page }) => {
    test.setTimeout(60_000)
    await page.goto(`/vms/${VM}?tab=snapshots`)
    await page.getByRole('button', { name: 'Take Snapshot' }).first().click()
    await page.locator('input').first().fill(SNAP)
    await page.getByRole('button', { name: 'Take Snapshot' }).last().click()
    await expect(page.getByText(SNAP, { exact: true })).toBeVisible({ timeout: 30_000 })
    await expect(page.getByText('[object Object]')).toHaveCount(0)
  })

  // 4 ── Export that snapshot as a template; verify it on the Images page.
  test('export the snapshot as a template and see it on Images', async ({ page }) => {
    test.setTimeout(120_000)
    await page.goto(`/vms/${VM}?tab=snapshots`)
    await expect(page.getByText(SNAP, { exact: true })).toBeVisible({ timeout: 20_000 })
    await page.getByRole('button', { name: 'Export' }).first().click()
    await page.getByPlaceholder('my-template-name').fill(TPL)
    // Export runs `qemu-img convert` synchronously (~20-60s). Wait for the POST to
    // finish before navigating — the Images page doesn't poll templates, so if we
    // land on /images before the export completes the template never shows up.
    await Promise.all([
      page.waitForResponse(
        r => r.url().includes(`/snapshots/${SNAP}/export`) && r.request().method() === 'POST',
        { timeout: 90_000 },
      ),
      page.getByRole('button', { name: 'Export Template' }).click(),
    ])

    await page.goto('/images')
    await expect(page.getByRole('heading', { name: 'VM Templates' })).toBeVisible()
    await expect(page.getByText(TPL, { exact: true })).toBeVisible({ timeout: 30_000 })
  })

  // 4b ── Provision a SECOND, independent VM FROM the exported template through
  //        the Provision UI (the core "create new VM from template" flow), and
  //        confirm it boots. Must run before the template is deleted (test 9):
  //        the new VM's disk is backed by the template qcow2.
  test('provision a new VM from the exported template', async ({ page }) => {
    // More headroom than the first provision: this VM boots while VM #1 is still
    // running, so the host is under more load and the IP lease can take longer.
    test.setTimeout(320_000)

    await page.goto('/provision')
    await page.getByLabel('VM Name').fill(VM2)
    await page.locator('#ssh-public-key').fill(SSH_KEY)

    // Image Source → "From Template", then pick the template we just exported.
    // The source <select> has no id; locate it by its 'From Template' option
    // (same approach as templates.spec.js). Template <option> value = name.
    const sourceSelect = page.locator('select', {
      has: page.locator('option', { hasText: 'From Template' }),
    })
    await sourceSelect.selectOption('template')
    await page.getByLabel('Template', { exact: true }).selectOption(TPL)

    // NAT 'private' → fast IP lease (bridge would wait ~120s).
    await page.locator('select#network').selectOption('private')

    await page.getByRole('button', { name: 'Provision VM' }).click()
    await expect(page.getByText('VM Ready!')).toBeVisible({ timeout: 300_000 })
    await expect(page.getByText('[object Object]')).toHaveCount(0)
  })

  // 4c ── The template-provisioned VM shows up in the dashboard VM list.
  test('template-provisioned VM appears in the dashboard list', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText(VM2, { exact: true }).first()).toBeVisible({ timeout: 20_000 })
  })

  // 5 ── Restore the snapshot through the UI.
  test('restore the snapshot', async ({ page }) => {
    test.setTimeout(60_000)
    await page.goto(`/vms/${VM}?tab=snapshots`)
    await expect(page.getByText(SNAP, { exact: true })).toBeVisible({ timeout: 20_000 })
    await page.getByRole('button', { name: 'Restore', exact: true }).first().click()
    await page.getByRole('button', { name: 'Restore', exact: true }).last().click()
    // The snapshot row persists after restore (use .first(): the confirm modal
    // also contains the snapshot name in a <strong> while it closes).
    await expect(page.getByText(SNAP, { exact: true }).first()).toBeVisible({ timeout: 30_000 })
    await expect(
      page.locator('[style*="border-left: 3px solid rgb(244, 63, 94)"]')
    ).toHaveCount(0)
  })

  // 6 ── Delete the snapshot through the UI.
  test('delete the snapshot', async ({ page }) => {
    test.setTimeout(60_000)
    await page.goto(`/vms/${VM}?tab=snapshots`)
    await expect(page.getByText(SNAP, { exact: true })).toBeVisible({ timeout: 20_000 })
    const row = page
      .locator('div')
      .filter({ has: page.getByRole('button', { name: 'Restore', exact: true }) })
      .filter({ hasText: SNAP })
      .last()
    await row.getByRole('button').last().click()          // trash (icon-only)
    await page.getByRole('button', { name: 'Delete', exact: true }).last().click()
    await expect(page.getByText(SNAP, { exact: true })).toHaveCount(0, { timeout: 20_000 })
  })

  // 7 ── Update the VM's network (allowed while running; applies on next boot).
  test('update the VM network', async ({ page }) => {
    test.setTimeout(60_000)
    await page.goto(`/vms/${VM}?tab=network`)
    await expect(page.locator('select#network')).toBeVisible({ timeout: 15_000 })
    // Switch NAT 'private' → 'default' (also NAT). Round-trips the update API.
    await page.locator('select#network').selectOption('default')
    await page.getByRole('button', { name: 'Apply Changes' }).click()
    await expect(page.getByText(`VM ${VM} network updated`)).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText('[object Object]')).toHaveCount(0)
  })

  // 8 ── Stop the VM (graceful ACPI; a real Ubuntu cloud image powers off), then
  //      resize CPU/RAM while stopped.
  test('stop the VM then resize CPU/RAM', async ({ page }) => {
    test.setTimeout(240_000)

    // Stop
    await page.goto(`/vms/${VM}`)
    await page.getByRole('button', { name: 'Stop', exact: true }).click()
    await expect(page.getByText(`VM ${VM} stopped`)).toBeVisible({ timeout: 15_000 })

    // Wait for the guest to actually power off (resize requires shutoff). A fresh
    // cloud image can take a while to finish first-boot before honouring ACPI.
    await expect(async () => {
      await page.goto(`/vms/${VM}`)
      await expect(page.getByText('shutoff', { exact: true }).first()).toBeVisible()
    }).toPass({ timeout: 200_000, intervals: [3_000] })

    // Resize: move CPU and RAM sliders (DiscreteSlider renders <input type=range>;
    // order is CPU, RAM, Disk). fill() sets the value by option index.
    await page.goto(`/vms/${VM}?tab=resize`)
    const sliders = page.locator('input[type="range"]')
    await expect(sliders.first()).toBeVisible({ timeout: 15_000 })
    // Grow CPU (2→4) and RAM (2048→4096); disk stays 20 GB (no-op). Growing
    // avoids the separate "shrink RAM below current config memory" edge case.
    await sliders.nth(0).fill('2')   // CPU options [1,2,4,8] → index 2 = 4
    await sliders.nth(1).fill('3')   // RAM options [512,1024,2048,4096,8192] → index 3 = 4096
    await page.getByRole('button', { name: 'Apply Changes' }).click()
    await expect(page.getByText(`VM ${VM} resized`)).toBeVisible({ timeout: 30_000 })
    await expect(page.getByText('[object Object]')).toHaveCount(0)
  })

  // 8c ── Delete the template-provisioned VM through the UI. Must run BEFORE the
  //        template is deleted (next test) — its disk is backed by the template.
  test('delete the template-provisioned VM', async ({ page }) => {
    test.setTimeout(60_000)
    await page.goto(`/vms/${VM2}`)
    await page.getByRole('button', { name: 'Delete VM', exact: true }).click()
    await page.getByRole('button', { name: 'Delete', exact: true }).last().click()
    await expect(async () => {
      await page.goto('/')
      await expect(page.getByText(VM2, { exact: true })).toHaveCount(0)
    }).toPass({ timeout: 30_000, intervals: [2_000] })
  })

  // 9 ── Delete the exported template through the Images UI.
  test('delete the template from Images', async ({ page }) => {
    test.setTimeout(60_000)
    await page.goto('/images')
    await expect(page.getByText(TPL, { exact: true })).toBeVisible({ timeout: 20_000 })
    const row = page.locator('tr').filter({ hasText: TPL })
    await row.getByRole('button', { name: 'Delete' }).click()
    await page.getByRole('button', { name: 'Delete', exact: true }).last().click()
    await expect(page.getByText(TPL, { exact: true })).toHaveCount(0, { timeout: 20_000 })
  })

  // 10 ── Delete the VM through the UI; confirm it leaves the list.
  test('delete the VM', async ({ page }) => {
    test.setTimeout(60_000)
    await page.goto(`/vms/${VM}`)
    await page.getByRole('button', { name: 'Delete VM', exact: true }).click()
    await page.getByRole('button', { name: 'Delete', exact: true }).last().click()
    await expect(async () => {
      await page.goto('/')
      await expect(page.getByText(VM, { exact: true })).toHaveCount(0)
    }).toPass({ timeout: 30_000, intervals: [2_000] })
  })
})

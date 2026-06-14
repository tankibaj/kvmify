import { test, expect } from '@playwright/test'
import { execSync } from 'node:child_process'
import { writeFileSync, rmSync } from 'node:fs'

// ⛔ PRODUCTION SAFETY: this is the ONLY destructive/mutating e2e. It NEVER
// touches a production VM. beforeAll creates a throwaway, powered-off,
// volume-backed domain (prefix `kvmify-e2e-`); afterAll destroys it and any
// artifacts. The test drives the real snapshot → export → delete workflow
// through the UI (the path that unit tests mock and non-destructive specs skip).
//
// Runs on the host (where virsh + the pool live): npm run test:e2e.

const VM = 'kvmify-e2e-tpl'
const VOL = `${VM}-root`
const POOL = 'default'
const SNAP = 'e2e-snap'
const TPL = 'kvmify-e2e-template'
const TPL_DIR = '/mnt/nvme1/kvm/pool/templates'

const sh = (cmd) => execSync(cmd, { stdio: 'pipe' }).toString().trim()
const quiet = (cmd) => { try { sh(cmd) } catch { /* idempotent cleanup */ } }

const DOMAIN_XML = `<domain type='kvm'>
  <name>${VM}</name>
  <memory unit='MiB'>128</memory>
  <vcpu>1</vcpu>
  <os><type arch='x86_64' machine='pc'>hvm</type></os>
  <devices>
    <disk type='volume' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source pool='${POOL}' volume='${VOL}'/>
      <target dev='vda' bus='virtio'/>
    </disk>
  </devices>
</domain>`

test.describe.serial('Snapshot → Template lifecycle (throwaway VM, never production)', () => {
  test.beforeAll(() => {
    // Clean any leftovers from a previous aborted run, then create fresh.
    quiet(`sudo -n virsh -c qemu:///system undefine ${VM} --snapshots-metadata`)
    quiet(`sudo -n virsh -c qemu:///system vol-delete ${VOL} --pool ${POOL}`)
    sh(`sudo -n virsh -c qemu:///system vol-create-as ${POOL} ${VOL} 64M --format qcow2`)
    writeFileSync(`/tmp/${VM}.xml`, DOMAIN_XML)
    sh(`sudo -n virsh -c qemu:///system define /tmp/${VM}.xml`)
  })

  test.afterAll(() => {
    quiet(`sudo -n virsh -c qemu:///system snapshot-delete ${VM} ${SNAP}`)
    quiet(`sudo -n virsh -c qemu:///system undefine ${VM} --snapshots-metadata`)
    quiet(`sudo -n virsh -c qemu:///system vol-delete ${VOL} --pool ${POOL}`)
    quiet(`rm -f ${TPL_DIR}/${TPL}.qcow2 ${TPL_DIR}/${TPL}.json`)
    quiet(`rm -f /tmp/${VM}.xml`)
  })

  test('take snapshot, export as template, verify on Images, delete template', async ({ page }) => {
    test.setTimeout(90_000) // qemu-img convert + libvirt ops

    // --- Take a snapshot through the UI (would have caught the field-mismatch bug) ---
    await page.goto(`/vms/${VM}`)
    await page.getByText('Snapshots', { exact: true }).first().click()
    await page.getByRole('button', { name: 'Take Snapshot' }).first().click()

    // Modal is open (portal at end of body): first visible input is the name.
    await page.locator('input').first().fill(SNAP)
    await page.getByRole('button', { name: 'Take Snapshot' }).last().click()

    // Snapshot row appears — proves the create round-trip actually succeeded.
    await expect(page.getByText(SNAP, { exact: true })).toBeVisible({ timeout: 30_000 })

    // --- Export that snapshot as a template ---
    await page.getByRole('button', { name: 'Export' }).first().click()
    await page.getByPlaceholder('my-template-name').fill(TPL)
    await page.getByRole('button', { name: 'Export Template' }).click()

    // --- Verify it shows up on the Images page ---
    await page.goto('/images')
    await expect(page.getByRole('heading', { name: 'VM Templates' })).toBeVisible()
    await expect(page.getByText(TPL, { exact: true })).toBeVisible({ timeout: 30_000 })

    // --- Delete the template through the UI and confirm it's gone ---
    await page.getByRole('button', { name: 'Delete' }).first().click()
    await page.getByRole('button', { name: 'Delete' }).last().click()
    await expect(page.getByText(TPL, { exact: true })).toHaveCount(0, { timeout: 15_000 })
  })
})

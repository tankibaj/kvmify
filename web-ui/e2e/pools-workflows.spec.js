import { test, expect, request } from '@playwright/test'

// Storage Pools workflows — PURE BROWSER. No virsh, no SSH.
//
// Creates its OWN throwaway pool through the UI (the backend builds the target
// directory), exercises stop/start/set-default/delete through the UI, and cleans
// up via the public HTTP API. Runs from a plain browser, locally or on the host.
//
// ⛔ PRODUCTION SAFETY: never deletes or permanently re-defaults the pre-existing
// `default` pool. If a test sets the throwaway as default, it is restored before
// the spec ends (and afterAll restores it again over HTTP as a backstop).

const POOL = 'kvmify-e2e-pool'
const DIR  = `/mnt/nvme1/kvm/pool/${POOL}`
const BASE = process.env.PLAYWRIGHT_BASE_URL || 'http://192.168.178.101'

async function cleanup() {
  const ctx = await request.newContext({ baseURL: BASE })
  // Always restore `default` as the KVMify default, then remove the throwaway.
  await ctx.post('/api/pools/default/default').catch(() => {})
  await ctx.delete(`/api/pools/${POOL}`).catch(() => {})
  await ctx.dispose()
}

async function gotoPools(page) {
  await page.goto('/pools')
  await expect(page.getByRole('heading', { name: 'Storage Pools' }).first()).toBeVisible()
}

// Match a pool's table row by its Name cell (first <td>), so the "default" badge
// in the Default column can't cause a false match for poolRow('default').
function poolRow(page, name) {
  return page
    .locator('tr')
    .filter({ has: page.locator('td:first-child').filter({ hasText: name }) })
    .first()
}

test.describe.serial('Storage pools workflows (self-created throwaway pool, never production)', () => {
  test.beforeAll(async () => { await cleanup() })
  test.afterAll(async () => { await cleanup() })

  // 1 ── Page loads and the production `default` pool is listed.
  test('pools page lists the default pool', async ({ page }) => {
    await gotoPools(page)
    await expect(poolRow(page, 'default')).toBeVisible()
    await expect(page.locator('body')).not.toContainText('[object Object]')
  })

  // 2 ── Create a pool through the Create Pool modal (backend builds the dir).
  test('create a pool via the Create Pool modal', async ({ page }) => {
    test.setTimeout(45_000)
    await gotoPools(page)
    await page.getByRole('button', { name: 'Create Pool' }).first().click()
    await expect(page.getByText('Create Storage Pool')).toBeVisible()
    await page.getByLabel('Pool Name').fill(POOL)
    await page.getByLabel('Target Path').fill(DIR)
    await page.getByRole('button', { name: 'Create Pool' }).last().click()

    await gotoPools(page)
    await expect(poolRow(page, POOL)).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('body')).not.toContainText('[object Object]')
  })

  // 3 ── Deactivate then reactivate the pool.
  test('stop then start the throwaway pool', async ({ page }) => {
    test.setTimeout(45_000)
    await gotoPools(page)
    // `exact: true`: a plain name:'Start' also substring-matches the "Autostart" toggle.
    const stopBtn = poolRow(page, POOL).getByRole('button', { name: 'Stop', exact: true })
    if (await stopBtn.isVisible()) {
      await stopBtn.click()
      await gotoPools(page)
    }
    const startBtn = poolRow(page, POOL).getByRole('button', { name: 'Start', exact: true })
    await expect(startBtn).toBeVisible({ timeout: 10_000 })
    await startBtn.click()
    await gotoPools(page)
    await expect(poolRow(page, POOL).getByRole('button', { name: 'Stop', exact: true })).toBeVisible({ timeout: 10_000 })
  })

  // 4 ── Set the throwaway as default, then restore `default` as default.
  test('set throwaway as default then restore default', async ({ page }) => {
    test.setTimeout(45_000)
    await gotoPools(page)

    const setBtn = poolRow(page, POOL).getByRole('button', { name: 'Set Default' })
    await expect(setBtn).toBeVisible()
    await setBtn.click()
    await gotoPools(page)
    await expect(poolRow(page, POOL).getByRole('button', { name: 'Set Default' })).toHaveCount(0)

    // Restore: make `default` the default again.
    const restore = poolRow(page, 'default').getByRole('button', { name: 'Set Default' })
    await expect(restore).toBeVisible()
    await restore.click()
    await gotoPools(page)
    await expect(poolRow(page, 'default').getByRole('button', { name: 'Set Default' })).toHaveCount(0)
    await expect(page.locator('body')).not.toContainText('[object Object]')
  })

  // 5 ── Delete the throwaway pool; `default` remains.
  test('delete the throwaway pool', async ({ page }) => {
    test.setTimeout(45_000)
    await gotoPools(page)
    await poolRow(page, POOL).getByRole('button', { name: 'Delete', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Delete Pool' })).toBeVisible()
    await page.getByRole('button', { name: 'Delete', exact: true }).last().click()
    await gotoPools(page)
    await expect(poolRow(page, POOL)).toHaveCount(0, { timeout: 15_000 })
    await expect(poolRow(page, 'default')).toBeVisible()
  })
})

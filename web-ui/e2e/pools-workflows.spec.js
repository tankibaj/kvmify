import { test, expect, request } from '@playwright/test'

// Storage Pools workflows — PURE BROWSER. No virsh, no SSH.
//
// Creates its OWN throwaway pool through the UI (the backend builds the target
// directory), exercises create/stop/start/delete through the UI, and cleans up
// via the public HTTP API. Runs from a plain browser, locally or on the host.
//
// ⛔ PRODUCTION SAFETY: only ever touches the self-created throwaway pool
// (prefix `kvmify-e2e-`). It NEVER stops, deletes, or re-defaults the
// pre-existing `default` pool — the set-default flow is intentionally not
// exercised so the host's KVMify default is never changed.
//
// Each mutating click waits for its API response BEFORE any page reload — a
// reload fired mid-request aborts the in-flight call (the stop never lands),
// which is what made the stop/start step flaky over a higher-latency tunnel.

const POOL = 'kvmify-e2e-pool'
const DIR  = `/mnt/nvme1/kvm/pool/${POOL}`
const BASE = process.env.PLAYWRIGHT_BASE_URL || 'http://192.168.178.101'

// Tear down ONLY our throwaway pool. Never touches the production `default` pool.
async function cleanup() {
  const ctx = await request.newContext({ baseURL: BASE })
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

// Click a button and wait for the resulting /api/pools request to complete, so a
// follow-up reload can't abort it. `method` defaults to PATCH (stop/start).
async function clickAndAwait(page, locator, { method = 'PATCH', urlPart = '/api/pools' } = {}) {
  await Promise.all([
    page.waitForResponse(r => r.url().includes(urlPart) && r.request().method() === method),
    locator.click(),
  ])
}

test.describe.serial('Storage pools workflows (self-created throwaway pool, never production)', () => {
  test.beforeAll(async () => { await cleanup() })
  test.afterAll(async () => { await cleanup() })

  // 1 ── Page loads and the production `default` pool is listed (read-only).
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
    // Wait for the POST to land before reloading (reload would abort the create).
    await clickAndAwait(page, page.getByRole('button', { name: 'Create Pool' }).last(), { method: 'POST' })

    await gotoPools(page)
    await expect(poolRow(page, POOL)).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('body')).not.toContainText('[object Object]')
  })

  // 3 ── Deactivate then reactivate the pool.
  test('stop then start the throwaway pool', async ({ page }) => {
    test.setTimeout(45_000)
    await gotoPools(page)
    // `exact: true`: a plain name:'Start' also substring-matches the "Autostart" toggle.
    // The pool is active right after create — auto-wait for the table to render its
    // Stop button (don't use isVisible(), which is an instant check and would skip
    // the stop if the pools fetch hasn't resolved yet).
    const stopBtn = poolRow(page, POOL).getByRole('button', { name: 'Stop', exact: true })
    await expect(stopBtn).toBeVisible({ timeout: 15_000 })
    // Wait for the stop PATCH to complete server-side before reloading.
    await clickAndAwait(page, stopBtn, { urlPart: `/api/pools/${POOL}` })

    await gotoPools(page)
    const startBtn = poolRow(page, POOL).getByRole('button', { name: 'Start', exact: true })
    await expect(startBtn).toBeVisible({ timeout: 15_000 })
    await clickAndAwait(page, startBtn, { urlPart: `/api/pools/${POOL}` })

    await gotoPools(page)
    await expect(poolRow(page, POOL).getByRole('button', { name: 'Stop', exact: true })).toBeVisible({ timeout: 15_000 })
  })

  // 4 ── Delete the throwaway pool; `default` remains.
  test('delete the throwaway pool', async ({ page }) => {
    test.setTimeout(45_000)
    await gotoPools(page)
    await poolRow(page, POOL).getByRole('button', { name: 'Delete', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Delete Pool' })).toBeVisible()
    // Wait for the DELETE to land before reloading.
    await clickAndAwait(page, page.getByRole('button', { name: 'Delete', exact: true }).last(), { method: 'DELETE', urlPart: `/api/pools/${POOL}` })
    await gotoPools(page)
    await expect(poolRow(page, POOL)).toHaveCount(0, { timeout: 15_000 })
    await expect(poolRow(page, 'default')).toBeVisible()
  })
})

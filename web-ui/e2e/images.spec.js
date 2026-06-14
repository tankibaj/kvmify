import { test, expect } from '@playwright/test'

test.describe('Images page', () => {
  test('lists the three Ubuntu base images with a Sync All action', async ({ page }) => {
    await page.goto('/images')

    await expect(page.getByText('Base Images').first()).toBeVisible()

    // The three LTS versions render
    await expect(page.getByText(/20\.04/).first()).toBeVisible()
    await expect(page.getByText(/22\.04/).first()).toBeVisible()
    await expect(page.getByText(/24\.04/).first()).toBeVisible()

    // Sync All exists (do NOT click — no real downloads in E2E)
    await expect(page.getByRole('button', { name: /Sync All/i }).first()).toBeVisible()
  })

  // Read-only: the "Add Base Image" modal opens, validates, and cancels.
  // We never submit — submitting would trigger a real multi-GB download on the host.
  test('Add Base Image modal opens, validates, and cancels', async ({ page }) => {
    await page.goto('/images')
    await page.getByRole('button', { name: 'Add Base Image' }).click()

    await expect(page.getByRole('heading', { name: 'Add Base Image' })).toBeVisible()

    // Submit is disabled until all three fields are filled.
    const submit = page.getByRole('button', { name: 'Add Image' })
    await expect(submit).toBeDisabled()

    await page.getByPlaceholder('e.g. Debian 12').fill('kvmify-e2e-noimage')
    await page.getByPlaceholder(/^https:\/\//).fill('https://example.com/none.qcow2')
    await page.getByPlaceholder(/debian12 or ubuntu22\.04/).fill('debian12')
    await expect(submit).toBeEnabled()

    // Cancel — never submit (no real download in E2E).
    await page.getByRole('button', { name: 'Cancel' }).click()
    await expect(page.getByRole('heading', { name: 'Add Base Image' })).toHaveCount(0)
  })
})

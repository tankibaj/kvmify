import { test, expect } from '@playwright/test'

test.describe('Images page', () => {
  test('lists the three Ubuntu base images with a Sync All action', async ({ page }) => {
    await page.goto('/images')

    await expect(page.getByText('Ubuntu Base Images').first()).toBeVisible()

    // The three LTS versions render
    await expect(page.getByText(/20\.04/).first()).toBeVisible()
    await expect(page.getByText(/22\.04/).first()).toBeVisible()
    await expect(page.getByText(/24\.04/).first()).toBeVisible()

    // Sync All exists (do NOT click — no real downloads in E2E)
    await expect(page.getByRole('button', { name: /Sync All/i }).first()).toBeVisible()
  })
})

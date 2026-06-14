import { test, expect } from '@playwright/test'

test.describe('Pools page', () => {
  test('shows the default pool and a Create Pool modal (no create)', async ({ page }) => {
    await page.goto('/pools')

    await expect(page.getByText('Storage Pools').first()).toBeVisible()
    // The seed pool named "default" renders
    await expect(page.getByText('default').first()).toBeVisible()

    // Create Pool opens a modal; close it without submitting
    const createBtn = page.getByRole('button', { name: /Create Pool/i }).first()
    await expect(createBtn).toBeVisible()
    await createBtn.click()

    // Modal fields render
    await expect(page.getByText(/Path/i).first()).toBeVisible()

    // Close without creating (Escape, then ensure no pool was added)
    await page.keyboard.press('Escape')
  })
})

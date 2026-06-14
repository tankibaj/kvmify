import { test, expect } from '@playwright/test'

test.describe('Sidebar navigation', () => {
  test('navigates between all pages', async ({ page }) => {
    await page.goto('/')

    await page.getByRole('link', { name: 'Images' }).click()
    await expect(page).toHaveURL(/\/images$/)
    await expect(page.getByText('Ubuntu Base Images').first()).toBeVisible()

    await page.getByRole('link', { name: 'Pools' }).click()
    await expect(page).toHaveURL(/\/pools$/)
    await expect(page.getByText('Storage Pools').first()).toBeVisible()

    await page.getByRole('link', { name: 'Provision' }).click()
    await expect(page).toHaveURL(/\/provision$/)
    await expect(page.getByRole('button', { name: /Provision VM/i }).first()).toBeVisible()

    await page.getByRole('link', { name: 'Dashboard' }).click()
    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByText('Virtual Machines').first()).toBeVisible()
  })
})

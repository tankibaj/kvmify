import { test, expect } from '@playwright/test'

test.describe('Dashboard', () => {
  test('renders header, stat cards, host stats, and VM table', async ({ page }) => {
    await page.goto('/')

    // Page header + New VM affordance
    await expect(page.getByText('Virtual Machines').first()).toBeVisible()
    await expect(page.getByRole('button', { name: /New VM/i }).first()).toBeVisible()

    // Sidebar live host stats
    await expect(page.getByText('CPU').first()).toBeVisible()
    await expect(page.getByText('RAM').first()).toBeVisible()
    await expect(page.getByText('Disk').first()).toBeVisible()

    // VM table renders rows for the real VMs (sandbox exists on the host),
    // or an empty state — accept either, but the page must not be blank.
    const hasSandbox = await page.getByText('sandbox').first().isVisible().catch(() => false)
    const hasEmpty = await page.getByText(/no virtual machines/i).first().isVisible().catch(() => false)
    expect(hasSandbox || hasEmpty).toBeTruthy()
  })
})

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
    // Sidebar shows absolute GB for RAM + Disk (regression: was "—/— GB").
    await expect(page.getByText(/\d+(\.\d+)?\/\d+ GB/).first()).toBeVisible()

    // Resource summary cards, including the CPU Allocated card.
    await expect(page.getByText('RAM Allocated').first()).toBeVisible()
    await expect(page.getByText('CPU Allocated').first()).toBeVisible()

    // VM table renders — either at least one VM row, or the empty state.
    // (No production VM name is hardcoded; the page just must not be blank.)
    const hasRows = await page.locator('table tbody tr').first().isVisible().catch(() => false)
    const hasEmpty = await page.getByText(/no virtual machines/i).first().isVisible().catch(() => false)
    expect(hasRows || hasEmpty).toBeTruthy()
  })
})

import { test, expect } from '@playwright/test'

// Uses the pre-existing 'sandbox' VM on the host. Read-only: no lifecycle,
// snapshot, resize, or network mutations are submitted.
test.describe('VM detail tabs', () => {
  test('renders all tabs for an existing VM without crashing', async ({ page }) => {
    await page.goto('/vms/sandbox')

    // Tab bar
    for (const tab of ['Overview', 'Console', 'Snapshots', 'Network', 'Resize']) {
      await expect(page.getByText(tab, { exact: true }).first()).toBeVisible()
    }

    // Snapshots tab → Take Snapshot affordance
    await page.getByText('Snapshots', { exact: true }).first().click()
    await expect(page.getByRole('button', { name: /Take Snapshot/i }).first()).toBeVisible()

    // Network tab → restart warning banner
    await page.getByText('Network', { exact: true }).first().click()
    await expect(page.getByText(/restart/i).first()).toBeVisible()

    // Resize tab → stop-required warning
    await page.getByText('Resize', { exact: true }).first().click()
    await expect(page.getByText(/stopped/i).first()).toBeVisible()

    // Console tab renders (may be "connecting"/"unavailable" — must not crash)
    await page.getByText('Console', { exact: true }).first().click()
    await expect(page).toHaveURL(/\/vms\/sandbox/)
  })
})

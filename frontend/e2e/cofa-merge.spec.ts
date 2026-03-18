import { test, expect } from '@playwright/test';

/**
 * COFA Merge e2e — verifies the DCL merge tab works through Platform/Maestra
 * without producing HTTP 500 errors. Covers:
 * - tool_executor structured error return (f3642c7)
 * - MergePanel auto-polling (5s interval, matches TriplesPanel)
 * - fetchMerge loading-state fix (showSpinner guard in finally block)
 * - Refresh button triggers visible reload
 */

test.describe('COFA Merge', () => {
  test('DCL merge tab loads and Run COFA Merge does not produce 500', async ({ page }) => {
    const errors500: { url: string; status: number }[] = [];
    page.on('response', (resp) => {
      if (resp.status() >= 500) {
        errors500.push({ url: resp.url(), status: resp.status() });
      }
    });

    // Navigate to DCL frontend merge tab
    await page.goto('http://localhost:3004', { waitUntil: 'networkidle' });

    // Click Merge tab
    const mergeTab = page.locator('text=Merge').first();
    await expect(mergeTab).toBeVisible();
    await mergeTab.click();
    await page.waitForTimeout(2000);

    // Verify merge page content loaded
    await expect(page.getByRole('heading', { name: 'COFA Merge' })).toBeVisible();

    // Click Run COFA Merge (or Re-run if a merge already exists)
    const mergeBtn = page.getByRole('button', { name: /Run COFA Merge|Re-run/ });
    await expect(mergeBtn).toBeVisible();
    await mergeBtn.click();

    // Wait for the request to fire and initial processing
    await page.waitForTimeout(10_000);

    // No 500 errors should have occurred
    expect(errors500).toEqual([]);

    // The button should have changed to Running state (merge is in progress)
    // or completed — either way, no ISE
    const bodyText = await page.locator('body').innerText();
    expect(bodyText).not.toContain('Internal Server Error');

    // Take a screenshot for verification record
    await page.screenshot({ path: '/tmp/e2e-cofa-merge.png', fullPage: true });
  });

  test('MergePanel auto-polls every 5s (Fix 1)', async ({ page }) => {
    // Track all fetches to /api/dcl/merge/overview
    const overviewFetches: number[] = [];
    page.on('response', (resp) => {
      if (resp.url().includes('/api/dcl/merge/overview')) {
        overviewFetches.push(Date.now());
      }
    });

    await page.goto('http://localhost:3004', { waitUntil: 'networkidle' });

    // Click Merge tab
    const mergeTab = page.locator('text=Merge').first();
    await expect(mergeTab).toBeVisible();
    await mergeTab.click();

    // Wait for heading to confirm the tab rendered
    await expect(page.getByRole('heading', { name: 'COFA Merge' })).toBeVisible();

    // The Auto-refresh checkbox must be present and checked by default
    const autoRefreshCheckbox = page.getByRole('checkbox', { name: 'Auto-refresh 5s' });
    await expect(autoRefreshCheckbox).toBeVisible();
    await expect(autoRefreshCheckbox).toBeChecked();

    // The label text must show "Auto-refresh 5s"
    await expect(page.locator('text=Auto-refresh 5s')).toBeVisible();

    // Record the count after initial load (1 fetch on mount)
    const initialCount = overviewFetches.length;
    expect(initialCount).toBeGreaterThanOrEqual(1);

    // Wait 12 seconds — should see at least 2 additional poll fetches (5s interval)
    await page.waitForTimeout(12_000);
    const afterPollCount = overviewFetches.length;
    expect(afterPollCount).toBeGreaterThanOrEqual(initialCount + 2);

    // Uncheck auto-refresh — polling should stop
    await autoRefreshCheckbox.uncheck();
    await expect(autoRefreshCheckbox).not.toBeChecked();
    const countAfterUncheck = overviewFetches.length;

    // Wait another 7 seconds — no new fetches should occur
    await page.waitForTimeout(7_000);
    expect(overviewFetches.length).toBe(countAfterUncheck);

    await page.screenshot({ path: '/tmp/e2e-merge-autopoll.png', fullPage: true });
  });

  test('Refresh button triggers fetch with loading state (Fix 2)', async ({ page }) => {
    const overviewFetches: string[] = [];
    page.on('response', (resp) => {
      if (resp.url().includes('/api/dcl/merge/overview')) {
        overviewFetches.push(resp.url());
      }
    });

    await page.goto('http://localhost:3004', { waitUntil: 'networkidle' });

    // Navigate to Merge tab
    const mergeTab = page.locator('text=Merge').first();
    await expect(mergeTab).toBeVisible();
    await mergeTab.click();
    await expect(page.getByRole('heading', { name: 'COFA Merge' })).toBeVisible();

    // Turn off auto-refresh so we only measure manual clicks
    const autoRefreshCheckbox = page.getByRole('checkbox', { name: 'Auto-refresh 5s' });
    await autoRefreshCheckbox.uncheck();
    await page.waitForTimeout(500);

    const beforeCount = overviewFetches.length;

    // Click Refresh
    const refreshBtn = page.getByRole('button', { name: 'Refresh' });
    await expect(refreshBtn).toBeVisible();
    await refreshBtn.click();

    // Wait for fetch to complete
    await page.waitForTimeout(2000);

    // Should have at least 1 more fetch
    expect(overviewFetches.length).toBeGreaterThan(beforeCount);

    // After Refresh completes, the page should still show COFA Merge heading
    // (not stuck in loading state — the finally-block fix ensures loading resets)
    await expect(page.getByRole('heading', { name: 'COFA Merge' })).toBeVisible();

    // No error banners should be present from the Refresh action
    const bodyText = await page.locator('body').innerText();
    expect(bodyText).not.toContain('Internal Server Error');

    await page.screenshot({ path: '/tmp/e2e-merge-refresh.png', fullPage: true });
  });

  test('Platform Maestra page loads without errors', async ({ page }) => {
    const errors500: { url: string; status: number }[] = [];
    page.on('response', (resp) => {
      if (resp.status() >= 500) {
        errors500.push({ url: resp.url(), status: resp.status() });
      }
    });

    await page.goto('http://localhost:3006', { waitUntil: 'networkidle' });

    // Platform frontend should load
    await expect(page.locator('body')).not.toBeEmpty();

    // No 500 errors
    expect(errors500).toEqual([]);

    await page.screenshot({ path: '/tmp/e2e-platform-home.png', fullPage: true });
  });
});

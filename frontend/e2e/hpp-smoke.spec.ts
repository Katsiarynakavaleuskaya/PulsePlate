import { expect, test } from '@playwright/test';
import type { Locator } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('pulseplate_api_key', 'playwright_smoke_key_12345');
  });
});

async function expectProtectedRouteOrAuthPrompt(routeHeading: Locator, authField: Locator) {
  try {
    await expect(routeHeading).toBeVisible({ timeout: 3_000 });
    return;
  } catch {
    await expect(authField).toBeVisible({ timeout: 3_000 });
  }
}

test('home shell renders', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Home' })).toBeVisible();
});

test('plate route renders', async ({ page }) => {
  await page.goto('/plate');
  await expectProtectedRouteOrAuthPrompt(
    page.getByRole('heading', { name: 'Your Plate' }),
    page.locator('#api-key-input')
  );
});

test('progress route renders', async ({ page }) => {
  await page.goto('/progress');
  await expectProtectedRouteOrAuthPrompt(
    page.getByRole('heading', { name: 'Progress' }),
    page.locator('#api-key-input')
  );
});

test('pro paywall route renders', async ({ page }) => {
  await page.goto('/pro');
  await expect(page.getByTestId('paywall-cta')).toBeVisible();
});

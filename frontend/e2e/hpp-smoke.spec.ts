import { expect, test } from '@playwright/test';
import type { Locator } from '@playwright/test';

async function expectProtectedRouteOrAuthPrompt(routeHeading: Locator, authField: Locator) {
  try {
    await expect(routeHeading).toBeVisible({ timeout: 3_000 });
    return;
  } catch {
    await expect(authField).toBeVisible({ timeout: 3_000 });
  }
}

test('home shell renders', async ({ page }) => {
  // Canonical in-app Home lives at /app; / is the marketing landing (hideTabBar).
  await page.goto('/app');
  await expect(
    page.getByRole('heading', {
      level: 1,
      name: 'Turn a check-in into practical meal decisions.',
    })
  ).toBeVisible();
  await expect(page.getByRole('link', { name: 'Continue planning' })).toBeVisible();
  await expect(page.getByRole('tablist', { name: 'Main tabs' })).toBeVisible();
});

test('plate route renders', async ({ page }) => {
  await page.goto('/plate');
  await expectProtectedRouteOrAuthPrompt(
    page.getByRole('heading', { name: 'Your Plate' }),
    page.locator('#api-key-input')
  );
  if ((await page.getByRole('heading', { name: 'Your Plate' }).count()) > 0) {
    await expect(page.getByRole('tablist', { name: 'Main tabs' })).toBeVisible();
  }
});

test('progress route renders', async ({ page }) => {
  await page.goto('/progress');
  await expectProtectedRouteOrAuthPrompt(
    page.getByRole('heading', { name: 'Progress' }),
    page.locator('#api-key-input')
  );
  if ((await page.getByRole('heading', { name: 'Progress' }).count()) > 0) {
    await expect(page.getByRole('link', { name: 'Update setup parameters' })).toBeVisible();
    await expect(page.getByRole('tablist', { name: 'Main tabs' })).toBeVisible();
  }
});

test('pro compatibility route renders the Apple-product information boundary', async ({ page }) => {
  await page.goto('/pro');
  await expect(
    page.getByRole('heading', { level: 1, name: 'PulsePlate for Apple devices' })
  ).toBeVisible();
  await expect(page.getByRole('link', { name: 'Try the free BMI calculator' })).toHaveAttribute(
    'href',
    '/bmi'
  );
  await expect(
    page.getByRole('link', { name: 'Learn about PulsePlate for Apple devices' })
  ).toHaveAttribute('href', '/marketing');
  await expect(
    page.getByRole('button', { name: /buy|subscribe|upgrade|trial|restore|payment/i })
  ).toHaveCount(0);
  await expect(
    page.getByRole('link', { name: /buy|subscribe|upgrade|trial|restore|payment/i })
  ).toHaveCount(0);
  await expect(page.getByTestId('paywall-cta')).toHaveCount(0);
  await expect(page.getByTestId('paywall-cancel')).toHaveCount(0);
  await expect(
    page.locator('a[href^="https://apps.apple.com"], a[href^="itms-apps:"]')
  ).toHaveCount(0);
});

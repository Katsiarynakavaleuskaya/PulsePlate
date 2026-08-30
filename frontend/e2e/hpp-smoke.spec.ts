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

const marketingViewportCases = [
  { width: 320, height: 900, demoColumns: 1, stepColumns: 1 },
  { width: 768, height: 1000, demoColumns: 1, stepColumns: 1 },
  { width: 1440, height: 1000, demoColumns: 2, stepColumns: 4 },
] as const;

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

for (const route of ['/', '/marketing'] as const) {
  test(`${route} renders the same deterministic FitChef preview`, async ({ page }) => {
    await page.goto(route);

    await expect(
      page.getByRole('heading', {
        level: 1,
        name: 'Check your BMI and see how FitChef works',
      })
    ).toBeVisible();
    await expect(
      page.getByRole('heading', {
        level: 2,
        name: 'See how FitChef helps you choose where to start',
      })
    ).toBeVisible();
    await expect(page.getByRole('link', { name: 'Return to the FitChef preview' })).toHaveAttribute(
      'href',
      '#fitchef-demo'
    );

    const today = page.getByRole('radio', { name: /Today/ });
    const week = page.getByRole('radio', { name: /This week/ });
    const confirm = page.getByRole('button', { name: 'Confirm choice' });

    await expect(confirm).toBeDisabled();
    await today.focus();
    await page.keyboard.press('Space');
    await expect(today).toBeChecked();
    await page.keyboard.press('ArrowRight');
    await expect(week).toBeFocused();
    await expect(week).toBeChecked();
    await expect(confirm).toBeEnabled();
    await confirm.focus();
    await page.keyboard.press('Enter');
    await expect(
      page.getByText('For this week, FitChef would point to Weekly Planning.')
    ).toBeVisible();

    await today.click();
    await expect(
      page.getByText('For this week, FitChef would point to Weekly Planning.')
    ).toHaveCount(0);
    await expect(page.getByRole('heading', { name: 'A place to begin' })).toHaveCount(0);
  });
}

for (const viewport of marketingViewportCases) {
  test(`marketing layout is bounded at exactly ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto('/marketing');

    const demoGrid = page.locator('.ppm-fitchef-demo-layout');
    const stepGrid = page.locator('.ppm-step-grid');
    await expect(demoGrid).toBeVisible();
    await expect(stepGrid).toBeVisible();
    await expect(stepGrid.locator('.ppm-step-card')).toHaveCount(4);

    const layout = await page.evaluate(() => {
      const demo = document.querySelector<HTMLElement>('.ppm-fitchef-demo-layout');
      const steps = document.querySelector<HTMLElement>('.ppm-step-grid');

      if (!demo || !steps) {
        throw new Error('Marketing layout grids not found');
      }

      const trackCount = (element: HTMLElement): number => {
        const columns = window.getComputedStyle(element).gridTemplateColumns.trim();
        return columns === '' || columns === 'none' ? 0 : columns.split(/\s+/).length;
      };

      return {
        viewportWidth: window.innerWidth,
        demoColumns: trackCount(demo),
        stepColumns: trackCount(steps),
        pageOverflows: document.documentElement.scrollWidth > document.documentElement.clientWidth,
        demoOverflows: demo.scrollWidth > demo.clientWidth,
        stepOverflows: steps.scrollWidth > steps.clientWidth,
        stepCardHeights: Array.from(steps.querySelectorAll<HTMLElement>('.ppm-step-card'), (card) =>
          Math.round(card.getBoundingClientRect().height)
        ),
      };
    });

    expect(layout.viewportWidth).toBe(viewport.width);
    expect(layout.demoColumns).toBe(viewport.demoColumns);
    expect(layout.stepColumns).toBe(viewport.stepColumns);
    expect(layout.pageOverflows).toBe(false);
    expect(layout.demoOverflows).toBe(false);
    expect(layout.stepOverflows).toBe(false);

    if (viewport.stepColumns === 4) {
      expect(new Set(layout.stepCardHeights).size).toBe(1);
    }
  });
}

test('FitChef preview stays usable at 320px, text spacing, and effective 200% zoom', async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/marketing');
  await page.addStyleTag({
    content: `
      .ppm-page,
      .ppm-page * {
        letter-spacing: 0.12em !important;
        line-height: 1.5 !important;
        word-spacing: 0.16em !important;
      }
      .ppm-page p {
        margin-bottom: 2em !important;
      }
    `,
  });

  const demo = page.locator('#fitchef-demo');
  const landing = page.locator('.ppm-page');
  await demo.scrollIntoViewIfNeeded();
  await expect(demo).toBeVisible();

  const hasNarrowOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth
  );
  expect(hasNarrowOverflow).toBe(false);
  expect(await landing.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(false);

  const option = page.getByRole('radio', { name: /Today/ }).locator('..');
  const optionBox = await option.boundingBox();
  const confirmBox = await page.getByRole('button', { name: 'Confirm choice' }).boundingBox();
  const notNowBox = await page.getByRole('button', { name: 'Not now' }).boundingBox();
  expect(optionBox?.height ?? 0).toBeGreaterThanOrEqual(44);
  expect(confirmBox?.height ?? 0).toBeGreaterThanOrEqual(44);
  expect(notNowBox?.height ?? 0).toBeGreaterThanOrEqual(44);

  const optionTransition = await option.evaluate((element) =>
    window.getComputedStyle(element).transitionDuration
  );
  expect(optionTransition).toBe('0s');

  await page.setViewportSize({ width: 640, height: 900 });
  await page.evaluate(() => {
    document.documentElement.style.zoom = '2';
  });
  const hasZoomOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth
  );
  expect(hasZoomOverflow).toBe(false);
  expect(await landing.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(false);
});

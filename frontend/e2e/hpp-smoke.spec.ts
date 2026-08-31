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
  { width: 320, height: 900, dailyColumns: 1 },
  { width: 768, height: 1000, dailyColumns: 1 },
  { width: 1440, height: 1000, dailyColumns: 2 },
] as const;

const promotedFitChefAssetPaths = [
  'activity-palette/endurance.webp',
  'activity-palette/movement-everyday-fitness.webp',
  'activity-palette/strength-power.webp',
  'activity-palette/team-combat.webp',
  'daily-plate-a-salmon-1024.webp',
  'food-context/food-context-ingredients-at-home.webp',
  'food-context/food-context-meal-photo.webp',
  'food-context/food-context-restaurant-chef.webp',
  'food-context/food-context-shopping-stores.webp',
  'vip/fitchef-vip-editorial-owner-approved-logo-v2.webp',
  'weekly-planning-a-meal-grid-1024.webp',
  'weekly-planning-b-notebook-1024.webp',
] as const;

const staticFitChefStoryNames = ['weekly', 'food-context', 'vip'] as const;

test('home shell renders', async ({ page }) => {
  // Canonical in-app Home lives at /app; / is the marketing landing (hideTabBar).
  await page.goto('/app');
  await expect(
    page.getByRole('heading', {
      level: 1,
      name: 'Turn a check-in into practical meal decisions.',
    }),
  ).toBeVisible();
  await expect(page.getByRole('link', { name: 'Continue planning' })).toBeVisible();
  await expect(page.getByRole('tablist', { name: 'Main tabs' })).toBeVisible();
});

test('plate route renders', async ({ page }) => {
  await page.goto('/plate');
  await expectProtectedRouteOrAuthPrompt(
    page.getByRole('heading', { name: 'Your Plate' }),
    page.locator('#api-key-input'),
  );
  if ((await page.getByRole('heading', { name: 'Your Plate' }).count()) > 0) {
    await expect(page.getByRole('tablist', { name: 'Main tabs' })).toBeVisible();
  }
});

test('progress route renders', async ({ page }) => {
  await page.goto('/progress');
  await expectProtectedRouteOrAuthPrompt(
    page.getByRole('heading', { name: 'Progress' }),
    page.locator('#api-key-input'),
  );
  if ((await page.getByRole('heading', { name: 'Progress' }).count()) > 0) {
    await expect(page.getByRole('link', { name: 'Update setup parameters' })).toBeVisible();
    await expect(page.getByRole('tablist', { name: 'Main tabs' })).toBeVisible();
  }
});

test('pro compatibility route renders the Apple-product information boundary', async ({ page }) => {
  await page.goto('/pro');
  await expect(
    page.getByRole('heading', { level: 1, name: 'PulsePlate for Apple devices' }),
  ).toBeVisible();
  await expect(page.getByRole('link', { name: 'Try the free BMI calculator' })).toHaveAttribute(
    'href',
    '/bmi',
  );
  await expect(
    page.getByRole('link', { name: 'Learn about PulsePlate for Apple devices' }),
  ).toHaveAttribute('href', '/marketing');
  await expect(
    page.getByRole('button', { name: /buy|subscribe|upgrade|trial|restore|payment/i }),
  ).toHaveCount(0);
  await expect(
    page.getByRole('link', { name: /buy|subscribe|upgrade|trial|restore|payment/i }),
  ).toHaveCount(0);
  await expect(page.getByTestId('paywall-cta')).toHaveCount(0);
  await expect(page.getByTestId('paywall-cancel')).toHaveCount(0);
  await expect(
    page.locator('a[href^="https://apps.apple.com"], a[href^="itms-apps:"]'),
  ).toHaveCount(0);
});

for (const route of ['/', '/marketing'] as const) {
  test(`${route} renders the same bounded four-part FitChef visual story`, async ({ page }) => {
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    const interactionRequests: Array<{ resourceType: string; url: string }> = [];

    page.on('console', (message) => {
      if (message.type() === 'error') {
        consoleErrors.push(message.text());
      }
    });
    page.on('pageerror', (error) => pageErrors.push(error.message));

    await page.goto(route);

    await expect(
      page.getByRole('heading', {
        level: 1,
        name: 'Check your BMI and see how FitChef works',
      }),
    ).toBeVisible();
    await expect(
      page.getByRole('heading', {
        level: 2,
        name: 'See how FitChef helps you choose where to start',
      }),
    ).toBeVisible();
    const demo = page.getByTestId('fitchef-value-demo');
    await expect(demo).toHaveCount(1);
    await expect(demo.locator('[data-fitchef-story]')).toHaveCount(4);
    expect(
      await demo
        .locator('[data-fitchef-story]')
        .evaluateAll((stories) => stories.map((story) => story.getAttribute('data-fitchef-story'))),
    ).toEqual(['daily', 'weekly', 'food-context', 'vip']);

    await expect(demo.getByRole('heading', { name: 'A week that changes with you' })).toBeVisible();
    await expect(
      demo.getByRole('heading', { name: 'A food plan built around real life' }),
    ).toBeVisible();
    await expect(
      demo.getByRole('heading', { name: 'Your personal AI nutrition guide' }),
    ).toBeVisible();
    await expect(page.getByRole('link', { name: 'Return to the FitChef preview' })).toHaveAttribute(
      'href',
      '#fitchef-demo',
    );

    for (const storyName of staticFitChefStoryNames) {
      const story = demo.locator(`[data-fitchef-story="${storyName}"]`);
      await expect(story).toBeVisible();
      await expect(
        story.locator(
          'a, button, input, select, textarea, fieldset, [role="button"], [role="link"], [role="radio"], [role="group"], [role="status"], [aria-live]',
        ),
      ).toHaveCount(0);
    }

    const promotedAssetMarkers = await demo
      .locator('img[data-fitchef-asset]')
      .evaluateAll((images) =>
        images.map((image) => image.getAttribute('data-fitchef-asset') ?? ''),
      );
    expect(promotedAssetMarkers).not.toContain('');
    expect(Array.from(new Set(promotedAssetMarkers)).sort()).toEqual(
      [...promotedFitChefAssetPaths].sort(),
    );
    const demoImages = demo.locator('img');
    expect(
      await demoImages.evaluateAll((images) =>
        images.every(
          (image) =>
            image.getAttribute('loading') === 'lazy' &&
            image.getAttribute('decoding') === 'async',
        ),
      ),
    ).toBe(true);
    for (let imageIndex = 0; imageIndex < (await demoImages.count()); imageIndex += 1) {
      await demoImages.nth(imageIndex).scrollIntoViewIfNeeded();
    }
    await expect
      .poll(async () =>
        demoImages.evaluateAll((images) =>
          images.every((image) => {
            const candidate = image as HTMLImageElement;
            return candidate.complete && candidate.naturalWidth > 0 && candidate.naturalHeight > 0;
          }),
        ),
      )
      .toBe(true);

    const storageBefore = await page.evaluate(() => ({
      local: Object.entries(localStorage).sort(),
      session: Object.entries(sessionStorage).sort(),
      cookie: document.cookie,
      hasGtag: typeof (window as Window & { gtag?: unknown }).gtag !== 'undefined',
      hasDataLayer: typeof (window as Window & { dataLayer?: unknown }).dataLayer !== 'undefined',
    }));
    const urlBefore = page.url();
    page.on('request', (request) => {
      interactionRequests.push({ resourceType: request.resourceType(), url: request.url() });
    });

    const dailyStory = demo.locator('[data-fitchef-story="daily"]');
    const today = dailyStory.getByRole('radio', { name: /Today/ });
    const week = dailyStory.getByRole('radio', { name: /This week/ });
    const todayLabel = today.locator('..');
    const weekLabel = week.locator('..');
    const confirm = dailyStory.getByRole('button', { name: 'Confirm choice' });
    const notNow = dailyStory.getByRole('button', { name: 'Not now' });
    await expect(
      dailyStory.getByRole('group', { name: 'Where would you like to start?' }),
    ).toHaveCount(1);
    await expect(dailyStory.getByRole('radio')).toHaveCount(2);
    await expect(dailyStory.getByRole('button')).toHaveCount(2);
    const readOptionVisualTreatment = async (radio: Locator, label: Locator) => {
      const labelVisual = await label.evaluate((element) => {
        const style = window.getComputedStyle(element);
        return {
          borderWidth: Number.parseFloat(style.borderTopWidth),
          boxShadow: style.boxShadow,
          background: style.backgroundColor,
          outlineWidth: Number.parseFloat(style.outlineWidth),
          outlineStyle: style.outlineStyle,
        };
      });
      const inputVisual = await radio.evaluate((element) => {
        const style = window.getComputedStyle(element);
        return {
          outlineWidth: Number.parseFloat(style.outlineWidth),
          outlineStyle: style.outlineStyle,
        };
      });

      return { label: labelVisual, input: inputVisual };
    };
    const hasVisibleOutline = (
      treatment: Awaited<ReturnType<typeof readOptionVisualTreatment>>,
    ): boolean =>
      (treatment.label.outlineWidth >= 2 && treatment.label.outlineStyle !== 'none') ||
      (treatment.input.outlineWidth >= 2 && treatment.input.outlineStyle !== 'none');

    const unselectedToday = await readOptionVisualTreatment(today, todayLabel);
    const unselectedWeek = await readOptionVisualTreatment(week, weekLabel);
    expect(unselectedToday.label.borderWidth).toBe(1);
    expect(unselectedToday.label.boxShadow).toBe('none');
    expect(unselectedToday.label.background).toBe(unselectedWeek.label.background);

    await expect(confirm).toBeDisabled();
    await today.focus();
    await page.keyboard.press('Space');
    await expect(today).toBeChecked();
    await expect
      .poll(async () => (await readOptionVisualTreatment(today, todayLabel)).label.borderWidth)
      .toBe(2);
    const selectedToday = await readOptionVisualTreatment(today, todayLabel);
    expect(selectedToday.label.borderWidth).toBe(2);
    expect(selectedToday.label.boxShadow).not.toBe('none');
    expect(selectedToday.label.boxShadow).toContain('inset');
    expect(selectedToday.label.background).not.toBe(unselectedToday.label.background);
    expect(hasVisibleOutline(selectedToday)).toBe(true);

    await confirm.focus();
    await page.keyboard.press('Enter');
    const todayResult = dailyStory.getByRole('status');
    await expect(todayResult.getByRole('heading', { name: 'Daily Plate' })).toBeVisible();
    await expect(todayResult.locator('img')).toHaveAttribute(
      'data-fitchef-asset',
      'daily-plate-a-salmon-1024.webp',
    );

    await today.focus();
    await page.keyboard.press('ArrowRight');
    await expect(week).toBeFocused();
    await expect(week).toBeChecked();
    await expect(today).not.toBeChecked();
    await expect(dailyStory.getByRole('status')).toHaveCount(0);
    await expect(dailyStory.getByRole('heading', { name: 'Daily Plate' })).toHaveCount(0);
    await expect
      .poll(async () => ({
        today: (await readOptionVisualTreatment(today, todayLabel)).label.borderWidth,
        week: (await readOptionVisualTreatment(week, weekLabel)).label.borderWidth,
      }))
      .toEqual({ today: 1, week: 2 });
    const clearedToday = await readOptionVisualTreatment(today, todayLabel);
    const selectedWeek = await readOptionVisualTreatment(week, weekLabel);
    expect(clearedToday.label.borderWidth).toBe(1);
    expect(clearedToday.label.boxShadow).toBe('none');
    expect(clearedToday.label.background).toBe(unselectedToday.label.background);
    expect(selectedWeek.label.borderWidth).toBe(2);
    expect(selectedWeek.label.boxShadow).not.toBe('none');
    expect(selectedWeek.label.boxShadow).toContain('inset');
    expect(selectedWeek.label.background).not.toBe(unselectedWeek.label.background);
    expect(hasVisibleOutline(selectedWeek)).toBe(true);

    await expect(confirm).toBeEnabled();
    await confirm.focus();
    await page.keyboard.press('Enter');
    const weekResult = dailyStory.getByRole('status');
    await expect(weekResult.getByRole('heading', { name: 'Weekly Planning' })).toBeVisible();
    await expect(weekResult.locator('img')).toHaveAttribute(
      'data-fitchef-asset',
      'weekly-planning-a-meal-grid-1024.webp',
    );

    await today.click();
    await expect(dailyStory.getByRole('status')).toHaveCount(0);
    await expect(dailyStory.getByRole('heading', { name: 'Weekly Planning' })).toHaveCount(0);
    await notNow.click();
    await expect(today).not.toBeChecked();
    await expect(week).not.toBeChecked();
    await expect(confirm).toBeDisabled();

    const storageAfter = await page.evaluate(() => ({
      local: Object.entries(localStorage).sort(),
      session: Object.entries(sessionStorage).sort(),
      cookie: document.cookie,
      hasGtag: typeof (window as Window & { gtag?: unknown }).gtag !== 'undefined',
      hasDataLayer: typeof (window as Window & { dataLayer?: unknown }).dataLayer !== 'undefined',
    }));
    const forbiddenInteractionRequests = interactionRequests.filter(({ resourceType }) =>
      ['fetch', 'xhr', 'eventsource', 'websocket'].includes(resourceType),
    );
    const externalInteractionRequests = interactionRequests.filter(({ url }) => {
      const candidate = new URL(url);
      return candidate.origin !== new URL(urlBefore).origin;
    });

    expect(forbiddenInteractionRequests).toEqual([]);
    expect(externalInteractionRequests).toEqual([]);
    expect(storageAfter).toEqual(storageBefore);
    expect(page.url()).toBe(urlBefore);
    expect(consoleErrors).toEqual([]);
    expect(pageErrors).toEqual([]);
  });
}

for (const viewport of marketingViewportCases) {
  test(`marketing layout is bounded at exactly ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto('/marketing');

    const storyRoot = page.getByTestId('fitchef-value-demo');
    const dailyFlow = storyRoot.locator('.ppm-fitchef-daily-flow');
    await expect(storyRoot).toBeVisible();
    await expect(storyRoot.locator('[data-fitchef-story]')).toHaveCount(4);
    await expect(dailyFlow).toBeVisible();

    const layout = await page.evaluate(() => {
      const root = document.querySelector<HTMLElement>('[data-testid="fitchef-value-demo"]');
      const daily = document.querySelector<HTMLElement>('.ppm-fitchef-daily-flow');

      if (!root || !daily) {
        throw new Error('FitChef story layout not found');
      }

      const trackCount = (element: HTMLElement): number => {
        const columns = window.getComputedStyle(element).gridTemplateColumns.trim();
        return columns === '' || columns === 'none' ? 0 : columns.split(/\s+/).length;
      };

      return {
        viewportWidth: window.innerWidth,
        dailyColumns: trackCount(daily),
        pageOverflows: document.documentElement.scrollWidth > document.documentElement.clientWidth,
        rootOverflows: root.scrollWidth > root.clientWidth,
        storyOverflows: Array.from(
          root.querySelectorAll<HTMLElement>('[data-fitchef-story]'),
          (story) => story.scrollWidth > story.clientWidth,
        ),
      };
    });

    expect(layout.viewportWidth).toBe(viewport.width);
    expect(layout.dailyColumns).toBe(viewport.dailyColumns);
    expect(layout.pageOverflows).toBe(false);
    expect(layout.rootOverflows).toBe(false);
    expect(layout.storyOverflows).toEqual([false, false, false, false]);
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
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(hasNarrowOverflow).toBe(false);
  expect(await landing.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(
    false,
  );

  const option = page.getByRole('radio', { name: /Today/ }).locator('..');
  const optionBox = await option.boundingBox();
  const confirmBox = await page.getByRole('button', { name: 'Confirm choice' }).boundingBox();
  const notNowBox = await page.getByRole('button', { name: 'Not now' }).boundingBox();
  expect(optionBox?.height ?? 0).toBeGreaterThanOrEqual(44);
  expect(confirmBox?.height ?? 0).toBeGreaterThanOrEqual(44);
  expect(notNowBox?.height ?? 0).toBeGreaterThanOrEqual(44);

  const optionTransition = await option.evaluate(
    (element) => window.getComputedStyle(element).transitionDuration,
  );
  expect(optionTransition).toBe('0s');

  const goalLayout = await demo.locator('.ppm-fitchef-goal-state').evaluateAll((states) =>
    states.map((state) => {
      const range = document.createRange();
      range.selectNodeContents(state);
      const lineTops = new Set(
        Array.from(range.getClientRects())
          .filter((rect) => rect.width > 0 && rect.height > 0)
          .map((rect) => Math.round(rect.top)),
      );

      return {
        lineCount: lineTops.size,
        overflows: state.scrollWidth > state.clientWidth,
      };
    }),
  );
  expect(goalLayout).toEqual([
    { lineCount: 1, overflows: false },
    { lineCount: 1, overflows: false },
    { lineCount: 1, overflows: false },
  ]);

  await page.setViewportSize({ width: 640, height: 900 });
  await page.evaluate(() => {
    document.documentElement.style.zoom = '2';
  });
  const hasZoomOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(hasZoomOverflow).toBe(false);
  expect(await landing.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(
    false,
  );
});

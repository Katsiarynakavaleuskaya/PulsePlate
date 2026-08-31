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
  { width: 900, height: 1100, dailyColumns: 1 },
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

const idleFitChefAssetMarkers = [
  'activity-palette/endurance.webp',
  'activity-palette/strength-power.webp',
  'activity-palette/team-combat.webp',
  'activity-palette/movement-everyday-fitness.webp',
  'weekly-planning-b-notebook-1024.webp',
  'food-context/food-context-restaurant-chef.webp',
  'food-context/food-context-ingredients-at-home.webp',
  'weekly-planning-a-meal-grid-1024.webp',
  'food-context/food-context-ingredients-at-home.webp',
  'food-context/food-context-restaurant-chef.webp',
  'food-context/food-context-shopping-stores.webp',
  'food-context/food-context-meal-photo.webp',
  'daily-plate-a-salmon-1024.webp',
  'weekly-planning-b-notebook-1024.webp',
  'vip/fitchef-vip-editorial-owner-approved-logo-v2.webp',
].sort();

const forbiddenStaticInteractionSelector = [
  'a',
  'button',
  'input',
  'select',
  'textarea',
  'fieldset',
  'form',
  'details',
  'summary',
  'audio[controls]',
  'video[controls]',
  'iframe',
  'object',
  'embed',
  '[contenteditable]:not([contenteditable="false"])',
  '[role="button"]',
  '[role="link"]',
  '[role="radio"]',
  '[role="group"]',
  '[role="status"]',
  '[aria-live]',
].join(', ');

const criticalFitChefCopySelector = [
  'h2',
  'h3',
  'p',
  'legend',
  'label',
  'button',
  '.ppm-fitchef-photo-card > span',
  '.ppm-fitchef-goal-state',
  '.ppm-fitchef-change > span:not(.ppm-fitchef-change-thumb)',
].join(', ');

async function readAssetMarkerMultiset(root: Locator): Promise<string[]> {
  return root
    .locator('img[data-fitchef-asset]')
    .evaluateAll((images) =>
      images.map((image) => image.getAttribute('data-fitchef-asset') ?? '').sort(),
    );
}

async function expectDecodedRevealImage(result: Locator, expectedBasename: string): Promise<void> {
  const image = result.locator('img');
  await expect(image).toHaveCount(1);
  await image.scrollIntoViewIfNeeded();
  await expect(image).toBeVisible();
  const decoded = await image.evaluate(async (node) => {
    const candidate = node as HTMLImageElement;
    if (!candidate.complete || candidate.naturalWidth === 0) {
      await candidate.decode();
    }
    return {
      path: new URL(candidate.currentSrc || candidate.src, document.baseURI).pathname,
      complete: candidate.complete,
      naturalWidth: candidate.naturalWidth,
      naturalHeight: candidate.naturalHeight,
    };
  });

  expect(decoded.path.endsWith(`/${expectedBasename}`)).toBe(true);
  expect(decoded.complete).toBe(true);
  expect(decoded.naturalWidth).toBeGreaterThan(0);
  expect(decoded.naturalHeight).toBeGreaterThan(0);
}

async function expectNoCriticalFitChefClipping(root: Locator): Promise<void> {
  const issues = await root.locator(criticalFitChefCopySelector).evaluateAll((elements) =>
    elements.flatMap((element) => {
      const candidate = element as HTMLElement;
      const style = window.getComputedStyle(candidate);
      const bounds = candidate.getBoundingClientRect();
      if (
        style.display === 'none' ||
        style.visibility === 'hidden' ||
        bounds.width === 0 ||
        bounds.height === 0
      ) {
        return [];
      }
      const range = document.createRange();
      range.selectNodeContents(candidate);
      const textIsClipped = Array.from(range.getClientRects()).some(
        (rect) =>
          rect.left < bounds.left - 1 ||
          rect.right > bounds.right + 1 ||
          rect.top < bounds.top - 1 ||
          rect.bottom > bounds.bottom + 1,
      );
      const boxIsClipped =
        (candidate.clientWidth > 0 && candidate.scrollWidth > candidate.clientWidth + 1) ||
        (candidate.clientHeight > 0 && candidate.scrollHeight > candidate.clientHeight + 1);
      return textIsClipped || boxIsClipped
        ? [{ tag: candidate.tagName, text: candidate.textContent?.trim() ?? '' }]
        : [];
    }),
  );

  expect(issues).toEqual([]);
}

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
    const observedRequests: Array<{ resourceType: string; url: string }> = [];

    page.on('console', (message) => {
      if (message.type() === 'error') {
        consoleErrors.push(message.text());
      }
    });
    page.on('pageerror', (error) => pageErrors.push(error.message));
    page.on('request', (request) => {
      observedRequests.push({ resourceType: request.resourceType(), url: request.url() });
    });

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
    await expect(demo.getByText('Maintain', { exact: true })).toHaveAttribute(
      'aria-current',
      'true',
    );
    await expect(page.getByRole('link', { name: 'Return to the FitChef preview' })).toHaveAttribute(
      'href',
      '#fitchef-demo',
    );

    for (const storyName of staticFitChefStoryNames) {
      const story = demo.locator(`[data-fitchef-story="${storyName}"]`);
      await expect(story).toBeVisible();
      await expect(story.locator(forbiddenStaticInteractionSelector)).toHaveCount(0);
      expect(
        await story
          .locator('*')
          .evaluateAll(
            (elements) =>
              elements.filter((element) => (element as HTMLElement).tabIndex >= 0).length,
          ),
      ).toBe(0);
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
    expect(promotedAssetMarkers.sort()).toEqual(idleFitChefAssetMarkers);
    const demoImages = demo.locator('img');
    expect(
      await demoImages.evaluateAll((images) =>
        images.every(
          (image) =>
            image.getAttribute('loading') === 'lazy' && image.getAttribute('decoding') === 'async',
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

    const cardImages = demo.locator('.ppm-fitchef-photo-card img');
    await expect(cardImages).toHaveCount(8);
    const cardImageDimensions: Array<{ width: number; height: number }> = [];
    for (let imageIndex = 0; imageIndex < (await cardImages.count()); imageIndex += 1) {
      const dimensions = await cardImages.nth(imageIndex).evaluate(
        async (node: Element): Promise<{ width: number; height: number }> => {
          if (!(node instanceof HTMLImageElement)) {
            throw new Error('FitChef card asset is not an image');
          }
          await node.decode();
          return { width: node.naturalWidth, height: node.naturalHeight };
        },
      );
      cardImageDimensions.push(dimensions);
    }
    expect(cardImageDimensions).toEqual(
      Array.from({ length: 8 }, (): { width: number; height: number } => ({
        width: 410,
        height: 512,
      })),
    );

    const foodStory = demo.locator('[data-fitchef-story="food-context"]');
    await expect(foodStory.getByRole('img', { name: 'Daily Plate example' })).toBeVisible();
    await expect(foodStory.getByRole('img', { name: 'Weekly Planning example' })).toBeVisible();

    const storageBefore = await page.evaluate(() => ({
      local: Object.entries(localStorage).sort(),
      session: Object.entries(sessionStorage).sort(),
      cookie: document.cookie,
      hasGtag: typeof (window as Window & { gtag?: unknown }).gtag !== 'undefined',
      hasDataLayer: typeof (window as Window & { dataLayer?: unknown }).dataLayer !== 'undefined',
    }));
    const urlBefore = page.url();

    const dailyStory = demo.locator('[data-fitchef-story="daily"]');
    const today = dailyStory.getByRole('radio', { name: /Today/ });
    const week = dailyStory.getByRole('radio', { name: /This week/ });
    const todayLabel = today.locator('..');
    const weekLabel = week.locator('..');
    const confirm = dailyStory.getByRole('button', { name: 'Confirm choice' });
    const notNow = dailyStory.getByRole('button', { name: 'Not now' });
    const persistentStatus = dailyStory.getByRole('status');
    await expect(
      dailyStory.getByRole('group', { name: 'Where would you like to start?' }),
    ).toHaveCount(1);
    await expect(dailyStory.getByRole('radio')).toHaveCount(2);
    await expect(dailyStory.getByRole('button')).toHaveCount(2);
    await expect(persistentStatus).toHaveCount(1);
    await expect(persistentStatus).toBeEmpty();
    await expect(persistentStatus).toHaveClass(/ppm-fitchef-reveal-card--empty/);
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
    const todayResult = persistentStatus;
    await expect(todayResult.getByRole('heading', { name: 'Daily Plate' })).toBeVisible();
    await expect(todayResult.locator('img')).toHaveAttribute(
      'data-fitchef-asset',
      'daily-plate-a-salmon-1024.webp',
    );
    await expectDecodedRevealImage(todayResult, 'daily-plate-a-salmon-1024.webp');
    expect(await readAssetMarkerMultiset(demo)).toEqual(
      [...idleFitChefAssetMarkers, 'daily-plate-a-salmon-1024.webp'].sort(),
    );

    await today.focus();
    await page.keyboard.press('ArrowRight');
    await expect(week).toBeFocused();
    await expect(week).toBeChecked();
    await expect(today).not.toBeChecked();
    await expect(persistentStatus).toBeEmpty();
    await expect(persistentStatus).toHaveClass(/ppm-fitchef-reveal-card--empty/);
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
    const weekResult = persistentStatus;
    await expect(weekResult.getByRole('heading', { name: 'Weekly Planning' })).toBeVisible();
    await expect(weekResult.locator('img')).toHaveAttribute(
      'data-fitchef-asset',
      'weekly-planning-a-meal-grid-1024.webp',
    );
    await expectDecodedRevealImage(weekResult, 'weekly-planning-a-meal-grid-1024.webp');
    expect(await readAssetMarkerMultiset(demo)).toEqual(
      [...idleFitChefAssetMarkers, 'weekly-planning-a-meal-grid-1024.webp'].sort(),
    );

    await today.click();
    await expect(persistentStatus).toBeEmpty();
    await expect(persistentStatus).toHaveClass(/ppm-fitchef-reveal-card--empty/);
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
    const forbiddenInteractionRequests = observedRequests.filter(({ resourceType }) =>
      ['fetch', 'xhr', 'eventsource', 'websocket'].includes(resourceType),
    );
    const externalInteractionRequests = observedRequests.filter(({ url }) => {
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

test('FitChef planning imagery stays square and uncropped at tablet and narrow widths', async ({
  page,
}) => {
  const assertSquareMedia = async (figures: Locator): Promise<void> => {
    await expect(figures).not.toHaveCount(0);

    for (let index = 0; index < (await figures.count()); index += 1) {
      const figure = figures.nth(index);
      const image = figure.locator('img');
      await figure.scrollIntoViewIfNeeded();
      await image.evaluate(async (node) => {
        const candidate = node as HTMLImageElement;
        if (!candidate.complete || candidate.naturalWidth === 0) {
          await candidate.decode();
        }
      });

      const media = await figure.evaluate((node) => {
        const candidate = node as HTMLElement;
        const bounds = candidate.getBoundingClientRect();
        const imageNode = candidate.querySelector('img');

        if (!(imageNode instanceof HTMLImageElement)) {
          throw new Error('Planning figure image not found');
        }

        return {
          aspect: bounds.width / bounds.height,
          objectFit: window.getComputedStyle(imageNode).objectFit,
          naturalAspect: imageNode.naturalWidth / imageNode.naturalHeight,
        };
      });

      expect(media.aspect).toBeGreaterThanOrEqual(0.99);
      expect(media.aspect).toBeLessThanOrEqual(1.01);
      expect(media.objectFit).toBe('contain');
      expect(media.naturalAspect).toBe(1);
    }
  };

  for (const viewport of [
    { width: 900, height: 1100 },
    { width: 320, height: 900 },
  ] as const) {
    await page.setViewportSize(viewport);
    await page.goto('/marketing');

    const demo = page.getByTestId('fitchef-value-demo');
    const dailyStory = demo.locator('[data-fitchef-story="daily"]');
    await dailyStory.getByRole('radio', { name: /Today/ }).click();
    await dailyStory.getByRole('button', { name: 'Confirm choice' }).click();
    const reveal = dailyStory.getByRole('status');
    await expectDecodedRevealImage(reveal, 'daily-plate-a-salmon-1024.webp');
    await assertSquareMedia(reveal.locator('.ppm-fitchef-reveal-photo'));

    if (viewport.width === 320) {
      await assertSquareMedia(
        demo.locator('[data-fitchef-story="food-context"] .ppm-fitchef-food-output figure'),
      );
    }
  }
});

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
  const dailyStory = demo.locator('[data-fitchef-story="daily"]');
  const today = dailyStory.getByRole('radio', { name: /Today/ });
  const option = today.locator('..');
  const confirm = dailyStory.getByRole('button', { name: 'Confirm choice' });
  const notNow = dailyStory.getByRole('button', { name: 'Not now' });

  const expectCoreStoryVisibleAndUnclipped = async (): Promise<void> => {
    for (const heading of [
      'See how FitChef helps you choose where to start',
      'A week that changes with you',
      'A food plan built around real life',
      'Your personal AI nutrition guide',
    ]) {
      await expect(demo.getByRole('heading', { name: heading })).toBeVisible();
    }
    await expect(
      dailyStory.getByRole('group', { name: 'Where would you like to start?' }),
    ).toBeVisible();
    await expect(today).toBeVisible();
    await expect(dailyStory.getByRole('radio', { name: /This week/ })).toBeVisible();
    await expect(confirm).toBeVisible();
    await expect(notNow).toBeVisible();
    await expectNoCriticalFitChefClipping(demo);
    expect(
      await demo.locator('[data-fitchef-story]').evaluateAll((stories) =>
        stories.map((story) => {
          const bounds = story.getBoundingClientRect();
          return bounds.left >= -1 && bounds.right <= document.documentElement.clientWidth + 1;
        }),
      ),
    ).toEqual([true, true, true, true]);
  };

  const expectTouchTargets = async (): Promise<void> => {
    for (const target of [option, confirm, notNow]) {
      const box = await target.boundingBox();
      expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
      expect(box?.width ?? 0).toBeGreaterThanOrEqual(44);
    }
  };

  const exerciseTransformedChoice = async (): Promise<void> => {
    await today.click();
    await confirm.click();
    const result = dailyStory.getByRole('status');
    await expect(result.getByRole('heading', { name: 'Daily Plate' })).toBeVisible();
    await expectDecodedRevealImage(result, 'daily-plate-a-salmon-1024.webp');
    await notNow.click();
    await expect(result).toBeEmpty();
    await expect(result).toHaveClass(/ppm-fitchef-reveal-card--empty/);
    await expect(today).not.toBeChecked();
    await expect(confirm).toBeDisabled();
  };

  const hasNarrowOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(hasNarrowOverflow).toBe(false);
  expect(await landing.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(
    false,
  );

  await expectCoreStoryVisibleAndUnclipped();
  await expectTouchTargets();

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
  await exerciseTransformedChoice();

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
  await expectCoreStoryVisibleAndUnclipped();
  await expectTouchTargets();
  await exerciseTransformedChoice();
});

import { createHash } from 'node:crypto';
import { lstatSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { expect, test } from '@playwright/test';
import type { Locator, Page, TestInfo } from '@playwright/test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import postcss from 'postcss';
import type { ProSessionStatus } from '../src/api/client';

const syntheticProSession: ProSessionStatus = {
  status: 'ok', authenticated: true, auth_source: 'cookie', tier: 'PRO',
};

async function stubProSession(page: Page, origin: string): Promise<() => number> {
  let calls = 0;
  await page.route(`${origin}/api/v1/pro/session`, async (route) => {
    const request = route.request();
    expect(request.method()).toBe('GET');
    expect(request.url()).toBe(`${origin}/api/v1/pro/session`);
    const headers = await request.allHeaders();
    expect(Boolean(headers.authorization || headers['x-api-key'] || headers.cookie)).toBe(false);
    calls += 1;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(syntheticProSession) });
  });
  return () => calls;
}

function expectRevealAssetIdentity(actualPath: string, expectedBasename: string): void {
  if (actualPath.endsWith(`/${expectedBasename}`)) {
    return;
  }
  // Vite hashes production filenames. Compare the actual built bytes with the
  // exact existing source asset; a filename-pattern match alone is insufficient.
  expect(['daily-plate-a-salmon-1024.webp', 'weekly-planning-a-meal-grid-1024.webp'])
    .toContain(expectedBasename);
  expect(actualPath.startsWith('/assets/')).toBe(true);
  const fileName = actualPath.slice('/assets/'.length);
  expect(/^[A-Za-z0-9_-]+\.webp$/.test(fileName)).toBe(true);
  expect(JSON.parse(readFileSync(resolve('package.json'), 'utf8')).name).toBe('pulseplate-frontend');
  const built = resolve('dist/assets', fileName);
  const source = resolve('src/assets/brand/fitchef-public-demo/v1', expectedBasename);
  for (const file of [source, built]) {
    const stat = lstatSync(file);
    expect(stat.isFile() && !stat.isSymbolicLink()).toBe(true);
  }
  const sha256 = (bytes: Uint8Array): string => createHash('sha256').update(bytes).digest('hex');
  expect(sha256(readFileSync(built))).toBe(sha256(readFileSync(source)));
}

async function expectProtectedRouteOrAuthPrompt(routeHeading: Locator, authField: Locator) {
  try {
    await expect(routeHeading).toBeVisible({ timeout: 3_000 });
    return;
  } catch {
    await expect(authField).toBeVisible({ timeout: 3_000 });
  }
}

const marketingViewportCases = [
  { width: 320, height: 900, dailyColumns: 1, heroColumns: 1 },
  { width: 768, height: 1000, dailyColumns: 1, heroColumns: 1 },
  { width: 900, height: 1100, dailyColumns: 1, heroColumns: 1 },
  { width: 1440, height: 1000, dailyColumns: 2, heroColumns: 2 },
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

  expectRevealAssetIdentity(decoded.path, expectedBasename);
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
  test(`${route} renders the same bounded four-part FitChef visual story`, async ({ page, baseURL }, testInfo) => {
    const origin = new URL(baseURL ?? '').origin;
    await stubProSession(page, origin);
    let interactionStarted = false;
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    const observedRequests: Array<{ resourceType: string; url: string; method: string; interaction: boolean }> = [];

    page.on('console', (message) => {
      if (message.type() === 'error') {
        consoleErrors.push(message.text());
      }
    });
    page.on('pageerror', (error) => pageErrors.push(error.message));
    page.on('request', (request) => {
      observedRequests.push({ resourceType: request.resourceType(), url: request.url(), method: request.method(), interaction: interactionStarted });
    });

    await page.goto(route);

    await expect(
      page.getByRole('heading', {
        level: 1,
        name: 'Check your BMI and see how FitChef works',
      }),
    ).toBeVisible();
    const hero = page.locator('#top');
    await expect(hero.getByRole('link', { name: 'See how FitChef works' })).toHaveAttribute(
      'href',
      '#fitchef-demo',
    );
    await expect(hero.getByRole('link', { name: 'Try the free BMI calculator' })).toHaveAttribute(
      'href',
      '/bmi',
    );
    const heroScenario = hero.locator('#product-preview');
    await expect(heroScenario).toHaveCount(1);
    await expect(heroScenario).toHaveJSProperty('tagName', 'FIGURE');
    const heroImage = hero.getByRole('img', {
      name: 'FitChef, a tabby cat stretching on an exercise mat',
    });
    await expect(heroImage).toHaveAttribute(
      'data-fitchef-hero-asset',
      'fitchef-hero-stretch-v1.webp',
    );
    await expect(heroImage).toHaveAttribute('loading', 'eager');
    await expect(heroImage).toHaveAttribute('fetchpriority', 'high');
    await expect(heroImage).toHaveAttribute('decoding', 'async');
    await expect(hero).not.toContainText('Wellness-safe guidance');
    await expect(hero).not.toContainText('Free on the web');
    await expect(hero).not.toContainText('Free website');
    await expect(hero).not.toContainText('No purchases here');
    await expect(hero).not.toContainText('Prepared FitChef preview');
    await expect(hero).not.toContainText('Prepared example');
    await expect(hero).not.toContainText('Nothing is saved');
    await expect(hero.locator('a[href^="https://apps.apple.com"], a[href^="itms-apps:"]')).toHaveCount(
      0,
    );
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
    await expect(
      demo.locator('[data-fitchef-story="vip"] img[data-fitchef-asset]'),
    ).toHaveAttribute('data-fitchef-asset', 'vip/fitchef-vip-editorial-owner-approved-logo-v2.webp');
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
    interactionStarted = true;

    const dailyStory = demo.locator('[data-fitchef-story="daily"]');
    const today = dailyStory.getByRole('radio', { name: /Today/ });
    const week = dailyStory.getByRole('radio', { name: /This week/ });
    const todayLabel = today.locator('..');
    const weekLabel = week.locator('..');
    const confirm = dailyStory.getByRole('button', { name: 'Confirm choice' });
    const notNow = dailyStory.getByRole('button', { name: 'Not now' });
    const persistentStatus = dailyStory.getByRole('status');
    const choiceGroup = dailyStory.getByRole('group', { name: 'Where would you like to start?' });
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
    await expect(choiceGroup).toHaveAttribute('data-keyboard-navigation', 'true');
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
    await testInfo.attach('radio-arrow-focus', {
      contentType: 'application/json',
      body: JSON.stringify({ treatment: selectedWeek, focus: await week.evaluate((element) => ({
        documentHasFocus: document.hasFocus(), visibility: document.visibilityState,
        active: document.activeElement === element, focusVisible: element.matches(':focus-visible'),
      })) }),
    });
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
    await expect(choiceGroup).not.toHaveAttribute('data-keyboard-navigation', 'true');
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
    await expect(choiceGroup).not.toHaveAttribute('data-keyboard-navigation', 'true');
    const pointerToday = await readOptionVisualTreatment(today, todayLabel);
    const nativePointerFocusVisible = await today.evaluate((element) => element.matches(':focus-visible'));
    if (!nativePointerFocusVisible) {
      expect(hasVisibleOutline(pointerToday)).toBe(false);
    }
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
    const forbiddenInteractionRequests = observedRequests.filter(({ resourceType, url, method, interaction }) =>
      ['fetch', 'xhr', 'eventsource', 'websocket'].includes(resourceType) &&
      !(interaction === false && resourceType === 'fetch' && method === 'GET' &&
        url === `${origin}/api/v1/pro/session`),
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
    const heroImage = page.locator('.ppm-hero-scenario-image');
    await expect(storyRoot).toBeVisible();
    await expect(storyRoot.locator('[data-fitchef-story]')).toHaveCount(4);
    await expect(dailyFlow).toBeVisible();
    await expect(heroImage).toBeVisible();
    await heroImage.evaluate((image) => (image as HTMLImageElement).decode());

    const layout = await page.evaluate(() => {
      const root = document.querySelector<HTMLElement>('[data-testid="fitchef-value-demo"]');
      const daily = document.querySelector<HTMLElement>('.ppm-fitchef-daily-flow');
      const heroGrid = document.querySelector<HTMLElement>('.ppm-hero-grid');
      const heroCopy = document.querySelector<HTMLElement>('.ppm-hero-copy');
      const heroScenario = document.querySelector<HTMLElement>('.ppm-hero-scenario');
      const heroMedia = document.querySelector<HTMLElement>('.ppm-hero-scenario-media');
      const heroImage = document.querySelector<HTMLImageElement>('.ppm-hero-scenario-image');

      if (!root || !daily || !heroGrid || !heroCopy || !heroScenario || !heroMedia || !heroImage) {
        throw new Error('FitChef Hero or story layout not found');
      }

      const trackCount = (element: HTMLElement): number => {
        const columns = window.getComputedStyle(element).gridTemplateColumns.trim();
        return columns === '' || columns === 'none' ? 0 : columns.split(/\s+/).length;
      };

      const heroCopyBounds = heroCopy.getBoundingClientRect();
      const heroScenarioBounds = heroScenario.getBoundingClientRect();
      const heroMediaBounds = heroMedia.getBoundingClientRect();

      return {
        viewportWidth: window.innerWidth,
        dailyColumns: trackCount(daily),
        heroColumns: trackCount(heroGrid),
        heroCopyPrecedesScenario: heroCopyBounds.top < heroScenarioBounds.top,
        heroMediaAspect: heroMediaBounds.width / heroMediaBounds.height,
        heroImageObjectFit: window.getComputedStyle(heroImage).objectFit,
        heroImageNaturalWidth: heroImage.naturalWidth,
        heroImageNaturalHeight: heroImage.naturalHeight,
        heroScenarioOverflows: heroScenario.scrollWidth > heroScenario.clientWidth,
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
    expect(layout.heroColumns).toBe(viewport.heroColumns);
    expect(layout.heroCopyPrecedesScenario).toBe(viewport.heroColumns === 1);
    expect(layout.heroMediaAspect).toBeGreaterThanOrEqual(0.799);
    expect(layout.heroMediaAspect).toBeLessThanOrEqual(0.801);
    expect(layout.heroImageObjectFit).toBe('contain');
    expect(layout.heroImageNaturalWidth).toBe(1122);
    expect(layout.heroImageNaturalHeight).toBe(1402);
    expect(layout.heroScenarioOverflows).toBe(false);
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

// The specimens render the current source components, not copied utility lists.
// Each worker uses frozen source; every page still receives fresh DOM and styles.
let compatibilitySpecimens: Promise<string> | undefined;

function renderCompatibilitySpecimens(): Promise<string> {
  compatibilitySpecimens ??= renderCompatibilitySpecimensUncached().catch((error) => {
    compatibilitySpecimens = undefined;
    throw error;
  });
  return compatibilitySpecimens;
}

async function renderCompatibilitySpecimensUncached(): Promise<string> {
  // Playwright's TSX transform produces transport descriptors, not React nodes.
  // Compile the actual source components through the existing Vite React pipeline.
  const { createServer } = await import('vite');
  const ssr = await createServer({
    root: resolve(),
    configFile: resolve('vite.config.ts'),
    envFile: false,
    appType: 'custom',
    optimizeDeps: { noDiscovery: true },
    server: { middlewareMode: true, ws: false, hmr: false, watch: null },
  });
  try {
    const { Button } = await ssr.ssrLoadModule('/src/components/ui/Button.tsx') as typeof import('../src/components/ui/Button');
    const { Card, CardContent } = await ssr.ssrLoadModule('/src/components/ui/Card.tsx') as typeof import('../src/components/ui/Card');
    const { Input } = await ssr.ssrLoadModule('/src/components/ui/Input.tsx') as typeof import('../src/components/ui/Input');
    const { Skeleton, ChartSkeleton, CardSkeleton } = await ssr.ssrLoadModule('/src/components/ui/Skeleton.tsx') as typeof import('../src/components/ui/Skeleton');
    const h = createElement;
    const specimens: string[] = [];
    const add = (id: string, node: Parameters<typeof renderToStaticMarkup>[0]): void => {
      specimens.push(renderToStaticMarkup(h('section', {
        'data-compat-section': id, style: { padding: 16, marginBottom: 16 },
      }, node)));
    };
    for (const variant of ['primary', 'secondary', 'destructive'] as const) {
      for (const state of ['default', 'disabled', 'loading'] as const) {
        const id = `button-${variant}-${state}`;
        add(id, h(Button, { variant, disabled: state === 'disabled', loading: state === 'loading',
          ...{ 'data-compat-target': id } }, id));
      }
    }
    for (const state of ['ordinary', 'invalid', 'disabled'] as const) {
      const id = `input-${state}`;
      add(id, h(Input, { invalid: state === 'invalid', disabled: state === 'disabled',
        'aria-label': id, placeholder: id, ...{ 'data-compat-target': id } }));
    }
    add('card', h(Card, { ...{ 'data-compat-target': 'card' } },
      h(CardContent, { ...{ 'data-compat-target': 'card-content' } }, 'Actual Card content')));
    add('skeleton', h(Skeleton, { ariaLabel: 'Owned skeleton', className: 'h-8 w-48',
      ...{ 'data-compat-target': 'skeleton' } }));
    add('chart-skeleton', h('div', { 'data-compat-target': 'chart-skeleton' }, h(ChartSkeleton)));
    add('card-skeleton', h('div', { 'data-compat-target': 'card-skeleton' }, h(CardSkeleton)));
    return specimens.join('');
  } finally {
    await ssr.close();
  }
}

async function showCompatibilitySpecimens(page: Page, origin: string): Promise<string> {
  await stubProSession(page, origin);
  await page.goto('/app');
  await expect(page.getByRole('heading', { level: 1, name: 'Turn a check-in into practical meal decisions.' })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  const styles = await page.locator('head style, head link[rel="stylesheet"]').evaluateAll((nodes) =>
    nodes.map((node) => node.outerHTML).join(''));
  expect(styles.length).toBeGreaterThan(0);
  const html = await renderCompatibilitySpecimens();
  await page.setContent(`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">${styles}</head><body><main>${html}</main></body></html>`);
  await page.evaluate(() => document.fonts.ready);
  await expect(page.locator('[data-compat-target="input-ordinary"]')).toHaveCSS('min-height', '44px');
  return html;
}

async function readCompatibilityStyle(node: Locator) {
  await expect(node).toHaveCount(1);
  await expect(node).toBeVisible();
  await expect.poll(() => node.evaluate((element) => {
    void getComputedStyle(element).transitionDuration;
    return element.getAnimations().filter((animation) =>
      animation.effect?.getTiming().iterations !== Infinity &&
      (animation.playState === 'running' || animation.pending)).length;
  })).toBe(0);
  return node.evaluate((element) => {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    const properties = ['background-color', 'color', 'border-top-width', 'border-top-style',
      'border-top-color', 'border-radius', 'padding-left', 'padding-right', 'padding-top',
      'padding-bottom', 'min-height', 'font-family', 'font-size', 'font-weight', 'line-height',
      'letter-spacing', 'box-shadow', 'outline-width', 'outline-style', 'outline-offset',
      'outline-color', 'opacity', 'cursor', 'animation-name', 'animation-duration',
      'transition-duration', 'forced-color-adjust', 'display', 'grid-template-columns',
      'flex-direction', 'gap', 'margin-top', 'margin-bottom'];
    if (rect.width <= 0 || rect.height <= 0) throw new Error('zero-area compatibility target');
    const scalar = (value: unknown): string | number | boolean | null => {
      if (typeof value === 'number') return Number.isFinite(value) ? value : String(value);
      if (typeof value === 'string' || typeof value === 'boolean') return value;
      return value == null ? null : String(value);
    };
    const animations = element.getAnimations().map((animation) => {
      const effect = animation.effect;
      const timing = effect?.getTiming();
      const computed = effect?.getComputedTiming();
      return {
        playState: animation.playState, pending: animation.pending,
        currentTime: scalar(animation.currentTime), playbackRate: scalar(animation.playbackRate),
        timing: timing ? Object.fromEntries((['delay', 'endDelay', 'fill', 'iterationStart',
          'iterations', 'duration', 'direction', 'easing'] as const).map((key) => [key, scalar(timing[key])])) : null,
        computedTiming: computed ? Object.fromEntries((['delay', 'endDelay', 'fill', 'iterationStart',
          'iterations', 'duration', 'direction', 'easing', 'endTime', 'activeDuration', 'localTime',
          'progress', 'currentIteration'] as const).map((key) => [key, scalar(computed[key])])) : null,
        keyframes: effect instanceof KeyframeEffect ? effect.getKeyframes().map((frame) =>
          Object.fromEntries((['offset', 'computedOffset', 'easing', 'composite', 'opacity', 'transform'] as const)
            .map((key) => [key, scalar(frame[key])]))) : null,
      };
    });
    // Resolve only the existing focus/surface tokens through the browser's own
    // serialization. This is a finite compatibility witness, not a color parser.
    const probe = document.createElement('span');
    probe.style.cssText = 'position:fixed;pointer-events:none;visibility:hidden;forced-color-adjust:none';
    for (const token of ['--color-primary', '--color-error', '--pp-blue', '--color-surface']) {
      probe.style.setProperty(token, style.getPropertyValue(token));
    }
    document.body.appendChild(probe);
    const color = (value: string): string => {
      probe.style.color = value;
      return getComputedStyle(probe).color;
    };
    const ring = (value: string): string => {
      // Existing input ring-2 plus ring-offset-1 has a 3px outer spread.
      probe.style.boxShadow = `0 0 0 3px var(${value})`;
      return getComputedStyle(probe).boxShadow;
    };
    const expectedFocus = {
      forcedColorsActive: matchMedia('(forced-colors: active)').matches,
      primary: color('var(--color-primary)'), brand: color('var(--pp-blue)'),
      highlight: color('Highlight'), canvasText: color('CanvasText'),
      surface: color('var(--color-surface)'),
      primaryRing: ring('--color-primary'), errorRing: ring('--color-error'),
    };
    probe.remove();
    return {
      expectedFocus,
      classes: element.className, width: rect.width, height: rect.height,
      rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
      disabled: (element instanceof HTMLButtonElement || element instanceof HTMLInputElement) && element.disabled,
      ariaInvalid: element.getAttribute('aria-invalid'), ariaBusy: element.getAttribute('aria-busy'),
      animations,
      children: Array.from(element.children).map((child) => {
        const childRect = child.getBoundingClientRect();
        const childStyle = getComputedStyle(child);
        return { tag: child.tagName, classes: child.className,
          rect: { x: childRect.x, y: childRect.y, width: childRect.width, height: childRect.height },
          display: childStyle.display, marginTop: childStyle.marginTop, marginBottom: childStyle.marginBottom };
      }),
      style: Object.fromEntries(properties.map((name) => [name, style.getPropertyValue(name)])),
      focus: { documentHasFocus: document.hasFocus(), visibility: document.visibilityState,
        active: document.activeElement === element, focusVisible: element.matches(':focus-visible') },
    };
  });
}

async function attachCompatibility(testInfo: TestInfo, name: string, observation: unknown): Promise<void> {
  await testInfo.attach(name, { contentType: 'application/json', body: JSON.stringify(observation, null, 2) });
}

async function keyboardCompatibilityTarget(page: Page, targetId: string, testInfo: TestInfo): Promise<void> {
  const expected = ['button-primary-default', 'button-secondary-default', 'button-destructive-default', 'input-ordinary', 'input-invalid'];
  const controls = await page.locator('[data-compat-target]').evaluateAll((nodes) => nodes.filter((node) =>
    (node instanceof HTMLButtonElement || node instanceof HTMLInputElement) && !node.disabled &&
    node.tabIndex >= 0 && node.getBoundingClientRect().width > 0 && node.getBoundingClientRect().height > 0)
    .map((node) => node.getAttribute('data-compat-target')));
  expect(controls).toEqual(expected);
  const index = expected.indexOf(targetId);
  expect(index).toBeGreaterThanOrEqual(0);
  const anchor = page.locator('[data-compat-section="button-primary-default"]');
  await anchor.scrollIntoViewIfNeeded();
  expect(await anchor.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    return document.elementFromPoint(rect.left + 1, rect.top + 1) === element;
  })).toBe(true);
  await anchor.click({ position: { x: 1, y: 1 } });
  for (let position = 0; position <= index; position += 1) {
    await page.keyboard.press('Tab');
    const intermediate = page.locator(`[data-compat-target="${expected[position]}"]`);
    await attachCompatibility(testInfo, `keyboard-${targetId}-${position}`, await readCompatibilityStyle(intermediate));
    await expect(intermediate).toBeFocused();
  }
}

function hasVisibleCompatibilityOutline(
  observation: Awaited<ReturnType<typeof readCompatibilityStyle>>,
  colors = [observation.expectedFocus.forcedColorsActive
    ? observation.expectedFocus.highlight : observation.expectedFocus.primary],
): boolean {
  return Number.parseFloat(observation.style['outline-width']) >= 2 &&
    observation.style['outline-style'] === 'solid' &&
    Number.parseFloat(observation.style['outline-offset']) >= 0 &&
    colors.includes(observation.style['outline-color']);
}

function expectVisibleCompatibilityOutline(observation: Awaited<ReturnType<typeof readCompatibilityStyle>>): void {
  expect(hasVisibleCompatibilityOutline(observation)).toBe(true);
}

function hasVisibleCompatibilityInputRing(
  observation: Awaited<ReturnType<typeof readCompatibilityStyle>>,
): boolean {
  const expected = observation.ariaInvalid === 'true'
    ? observation.expectedFocus.errorRing : observation.expectedFocus.primaryRing;
  return observation.focus.active && expected !== 'none' && expected !== '' &&
    observation.style['box-shadow'].includes(expected);
}

for (const width of [320, 1440] as const) {
  test(`source primitives preserve bounded CSS states at ${width}px`, async ({ page, baseURL, browserName, browser }, testInfo) => {
    await page.setViewportSize({ width, height: width === 320 ? 900 : 1000 });
    const html = await showCompatibilitySpecimens(page, new URL(baseURL ?? '').origin);
    const target = (id: string): Locator => page.locator(`[data-compat-target="${id}"]`);
    const defaults: Record<string, Awaited<ReturnType<typeof readCompatibilityStyle>>> = {};
    const specimenIds = [
      ...(['primary', 'secondary', 'destructive'] as const).flatMap((variant) =>
        (['default', 'disabled', 'loading'] as const).map((state) => `button-${variant}-${state}`)),
      'input-ordinary', 'input-invalid', 'input-disabled', 'card', 'skeleton', 'chart-skeleton', 'card-skeleton',
    ];
    expect(specimenIds).toHaveLength(16);
    await expect(page.locator('[data-compat-section]')).toHaveCount(specimenIds.length);
    expect(await page.locator('[data-compat-section]').evaluateAll((nodes) =>
      nodes.map((node) => node.getAttribute('data-compat-section')))).toEqual(specimenIds);
    const defaultTargets: [string, Locator][] = [
      ...specimenIds.map((id): [string, Locator] => [id, target(id)]),
      ['card-content', target('card-content')],
      ['card-skeleton-shadow', target('card-skeleton').locator(':scope > div')],
      ['chart-rounded-override', target('chart-skeleton').locator('.rounded-lg')],
    ];
    // Complete all independent default observations before any interaction.
    const observations = await Promise.all(defaultTargets.map(async ([id, node]) =>
      [id, await readCompatibilityStyle(node)] as const));
    for (const [id, observation] of observations) defaults[id] = observation;
    await attachCompatibility(testInfo, 'primitive-defaults', { viewport: page.viewportSize(), browserName, version: browser.version(),
      markupSha256: createHash('sha256').update(html).digest('hex'), specimenIds, defaults });
    expect(Object.keys(defaults)).toHaveLength(19);
    expect(defaults['input-invalid'].ariaInvalid).toBe('true');
    expect(defaults['input-disabled'].disabled).toBe(true);
    for (const variant of ['primary', 'secondary', 'destructive'] as const) {
      expect(defaults[`button-${variant}-disabled`].disabled).toBe(true);
      expect(defaults[`button-${variant}-loading`].disabled).toBe(true);
      expect(defaults[`button-${variant}-loading`].ariaBusy).toBe('true');
    }
    expect(defaults['button-primary-default'].style['min-height']).toBe('44px');
    expect(defaults['button-primary-default'].style['padding-left']).toBe('24px');
    expect(defaults['button-primary-default'].style['border-radius']).toBe('12px');
    expect(defaults['input-ordinary'].style['padding-left']).toBe('12px');
    expect(defaults['input-ordinary'].style['border-radius']).toBe('8px');
    expect(defaults['card-content'].style['padding-bottom']).toBe('24px');
    await expect(target('input-invalid')).toHaveAttribute('aria-invalid', 'true');
    await expect(target('input-disabled')).toBeDisabled();
    for (const variant of ['primary', 'secondary', 'destructive'] as const) {
      await expect(target(`button-${variant}-disabled`)).toBeDisabled();
      await expect(target(`button-${variant}-loading`)).toBeDisabled();
      await expect(target(`button-${variant}-loading`)).toHaveAttribute('aria-busy', 'true');
      const id = `button-${variant}-default`;
      const button = target(id);
      await button.hover();
      const hover = await readCompatibilityStyle(button);
      await page.mouse.down();
      let active;
      try { active = await readCompatibilityStyle(button); } finally { await page.mouse.up(); }
      await keyboardCompatibilityTarget(page, id, testInfo);
      const focus = await readCompatibilityStyle(button);
      await attachCompatibility(testInfo, id, { hover, active, focus });
      expectVisibleCompatibilityOutline(focus);
    }
    for (const state of ['ordinary', 'invalid'] as const) {
      await keyboardCompatibilityTarget(page, `input-${state}`, testInfo);
      const focused = await readCompatibilityStyle(target(`input-${state}`));
      await attachCompatibility(testInfo, `input-${state}-focus`, focused);
      expect(hasVisibleCompatibilityInputRing(focused)).toBe(true);
    }
    const chart = target('chart-skeleton').locator('.rounded-lg');
    expect((await chart.getAttribute('class'))?.split(/\s+/)).not.toContain('rounded-md');
    await expect(chart).toHaveCSS('border-radius', '8px');
  });
}

for (const theme of ['light', 'dark', null] as const) {
  test(`source theme/media observations for ${theme ?? 'auto'}`, async ({ page, baseURL, browserName, browser }, testInfo) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await showCompatibilitySpecimens(page, new URL(baseURL ?? '').origin);
    for (const colorScheme of ['light', 'dark'] as const) {
      for (const reducedMotion of ['no-preference', 'reduce'] as const) {
        await page.emulateMedia({ colorScheme, reducedMotion, forcedColors: 'none' });
        await page.evaluate((value) => {
          if (value === null) document.documentElement.removeAttribute('data-theme');
          else document.documentElement.setAttribute('data-theme', value);
        }, theme);
        const media = await page.evaluate(() => ({ theme: document.documentElement.getAttribute('data-theme'),
          dark: matchMedia('(prefers-color-scheme: dark)').matches, reduce: matchMedia('(prefers-reduced-motion: reduce)').matches,
          shadowSm: getComputedStyle(document.documentElement).getPropertyValue('--shadow-sm'),
          shadowMd: getComputedStyle(document.documentElement).getPropertyValue('--shadow-md') }));
        const card = await readCompatibilityStyle(page.locator('[data-compat-target="card"]'));
        const skeleton = await readCompatibilityStyle(page.locator('[data-compat-target="skeleton"]'));
        const cardSkeleton = await readCompatibilityStyle(page.locator('[data-compat-target="card-skeleton"] > div'));
        await page.locator('[data-compat-target="button-secondary-default"]').hover();
        const hover = await readCompatibilityStyle(page.locator('[data-compat-target="button-secondary-default"]'));
        await attachCompatibility(testInfo, `${theme ?? 'auto'}-${colorScheme}-${reducedMotion}`, {
          browserName, version: browser.version(), media, card, skeleton, cardSkeleton, hover });
        expect(media.dark).toBe(colorScheme === 'dark');
        expect(media.reduce).toBe(reducedMotion === 'reduce');
        expect(skeleton.style['border-radius']).toBe('6px');
        if (reducedMotion === 'reduce') {
          expect(skeleton.style['animation-name']).toBe('none');
          expect(skeleton.style['animation-duration']).toBe('0s');
          expect(skeleton.style.opacity).toBe('1');
          expect(hover.style['transition-duration']).toBe('0s');
        }
      }
    }
  });
}

test('forced-color input and button focus stays visible', async ({ page, baseURL }, testInfo) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await showCompatibilitySpecimens(page, new URL(baseURL ?? '').origin);
  for (const forcedColors of ['none', 'active'] as const) {
    await page.emulateMedia({ forcedColors });
    const observedActive = await page.evaluate(() => matchMedia('(forced-colors: active)').matches);
    for (const id of ['input-ordinary', 'input-invalid', 'button-primary-default', 'button-secondary-default']) {
      await keyboardCompatibilityTarget(page, id, testInfo);
      const observation = await readCompatibilityStyle(page.locator(`[data-compat-target="${id}"]`));
      await attachCompatibility(testInfo, `${id}-${forcedColors}`, { emulated: forcedColors, observedActive,
        unsupportedUnknown: forcedColors === 'active' && !observedActive, observation });
      expect(observation.focus.active).toBe(true);
      if (forcedColors === 'active' && observedActive) expectVisibleCompatibilityOutline(observation);
      else if (id.startsWith('input-')) expect(hasVisibleCompatibilityInputRing(observation)).toBe(true);
      else expectVisibleCompatibilityOutline(observation);
    }
  }
});

for (const forcedColors of ['none', 'active'] as const) {
  test(`radio arrows preserve focus and resets with forced colors ${forcedColors}`, async ({ page, baseURL }, testInfo) => {
  const origin = new URL(baseURL ?? '').origin;
  await stubProSession(page, origin);
  await page.setViewportSize({ width: 320, height: 900 });
  await page.goto('/marketing');
  const story = page.locator('[data-fitchef-story="daily"]');
  const group = story.getByRole('group', { name: 'Where would you like to start?' });
  const today = story.getByRole('radio', { name: /Today/ });
  const week = story.getByRole('radio', { name: /This week/ });
  const confirm = story.getByRole('button', { name: 'Confirm choice' });
  {
    await page.emulateMedia({ forcedColors });
    const observedActive = await page.evaluate(() => matchMedia('(forced-colors: active)').matches);
    for (const key of ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown']) {
      const backwards = key === 'ArrowLeft' || key === 'ArrowUp';
      const start = backwards ? week : today;
      const destination = backwards ? today : week;
      await start.click();
      await attachCompatibility(testInfo, `radio-start-${key}-${forcedColors}`, await readCompatibilityStyle(start));
      await expect(start).toBeFocused();
      await expect(start).toBeChecked();
      await page.keyboard.press(key);
      await expect(destination).toBeFocused();
      await expect(destination).toBeChecked();
      await expect(start).not.toBeChecked();
      await expect(group).toHaveAttribute('data-keyboard-navigation', 'true');
      const input = await readCompatibilityStyle(destination);
      const label = await readCompatibilityStyle(destination.locator('..'));
      await attachCompatibility(testInfo, `radio-${key}-${forcedColors}`, { observedActive, input, label });
      expect([input, label].some((node) => hasVisibleCompatibilityOutline(node,
        observedActive ? [node.expectedFocus.highlight, node.expectedFocus.canvasText]
          : [node.expectedFocus.brand]))).toBe(true);
      await today.click();
      await expect(group).not.toHaveAttribute('data-keyboard-navigation', 'true');
      const pointer = await readCompatibilityStyle(today.locator('..'));
      if (!await today.evaluate((element) => element.matches(':focus-visible'))) {
        expect(['none', 'hidden']).toContain(pointer.style['outline-style']);
      }
      await page.keyboard.press('ArrowRight');
      await expect(group).toHaveAttribute('data-keyboard-navigation', 'true');
      await page.keyboard.press('Tab');
      await expect(confirm).toBeFocused();
      await expect(group).not.toHaveAttribute('data-keyboard-navigation', 'true');
    }
  }
  });
}

test('focus witnesses reject transparent colors and zero-geometry shadows', async ({ page, baseURL }, testInfo) => {
  await showCompatibilitySpecimens(page, new URL(baseURL ?? '').origin);
  await keyboardCompatibilityTarget(page, 'button-primary-default', testInfo);
  const button = page.locator('[data-compat-target="button-primary-default"]');
  const originalButtonStyle = await button.getAttribute('style');
  const buttonBefore = await readCompatibilityStyle(button);
  expectVisibleCompatibilityOutline(buttonBefore);
  const outlineNegatives = [];
  try {
    for (const color of ['color(srgb 0 0 0 / 0)', 'rgba(51, 159, 255, 0.001)']) {
      await button.evaluate((element, value) => {
        (element as HTMLElement).style.outline = `2px solid ${value}`;
      }, color);
      const observed = await readCompatibilityStyle(button);
      outlineNegatives.push(observed);
      expect(hasVisibleCompatibilityOutline(observed)).toBe(false);
    }
    await button.evaluate((element) => {
      (element as HTMLElement).style.outline = '0px solid var(--color-primary)';
    });
    const zeroWidth = await readCompatibilityStyle(button);
    outlineNegatives.push(zeroWidth);
    expect(hasVisibleCompatibilityOutline(zeroWidth)).toBe(false);
  } finally {
    await button.evaluate((element, value) => {
      if (value === null) element.removeAttribute('style');
      else element.setAttribute('style', value);
    }, originalButtonStyle);
  }
  expectVisibleCompatibilityOutline(await readCompatibilityStyle(button));
  await keyboardCompatibilityTarget(page, 'input-ordinary', testInfo);
  const input = page.locator('[data-compat-target="input-ordinary"]');
  const originalInputStyle = await input.getAttribute('style');
  const inputBefore = await readCompatibilityStyle(input);
  expect(hasVisibleCompatibilityInputRing(inputBefore)).toBe(true);
  const ringNegatives = [];
  try {
    for (const shadow of ['0 0 0 3px rgba(51, 159, 255, 0)', '0 0 0 0 var(--color-primary)']) {
      await input.evaluate((element, value) => { (element as HTMLElement).style.boxShadow = value; }, shadow);
      const observed = await readCompatibilityStyle(input);
      ringNegatives.push(observed);
      expect(hasVisibleCompatibilityInputRing(observed)).toBe(false);
    }
  } finally {
    await input.evaluate((element, value) => {
      if (value === null) element.removeAttribute('style');
      else element.setAttribute('style', value);
    }, originalInputStyle);
  }
  expect(hasVisibleCompatibilityInputRing(await readCompatibilityStyle(input))).toBe(true);
  await attachCompatibility(testInfo, 'focus-negative-controls', { buttonBefore, outlineNegatives, inputBefore, ringNegatives });
});

test('CSS smoke rejects an exact missing grid despite grid-cols neighbors', async ({ page, baseURL }, testInfo) => {
  // Keep the native .mjs helper on Node's ESM loader instead of a transformed require.
  const { assertTailwindUtilities, assertBuiltCssEntry } = await import(pathToFileURL(resolve('scripts/check-tailwind-utilities.mjs')).href);
  const entry = '<link rel="stylesheet" href="/assets/index-proof.css">';
  const html = (content: string): string => `<!doctype html><html><head>${content}</head><body></body></html>`;
  const sentinel = '__pulseplateCssDomSmokeExecuted';
  expect(Object.prototype.hasOwnProperty.call(globalThis, sentinel)).toBe(false);
  const inert = [
    `<!-- ${entry} -->`,
    `<script>globalThis.${sentinel}=true; const link = '${entry}';</script>`,
    `<style>${entry}</style>`,
    `<title>${entry}</title>`,
    `<textarea>${entry}</textarea>`,
    `<template><template>${entry}</template></template>`,
    `<noscript>${entry}</noscript>`,
    `<plaintext>${entry}`,
  ];
  const rejected: string[] = [];
  for (const content of inert) {
    expect(() => assertBuiltCssEntry(html(content), 'index-proof.css')).toThrow('Built frontend index must reference');
    rejected.push(content);
  }
  const duplicateAttributes = [
    'rel="stylesheet" rel="preload" href="/assets/index-proof.css"',
    'rel="preload" rel="stylesheet" href="/assets/index-proof.css"',
    'REL="stylesheet" rel="preload" href="/assets/index-proof.css"',
    'rel="preload" ReL="stylesheet" href="/assets/index-proof.css"',
    'rel="stylesheet" href="/assets/index-proof.css" href="/assets/index-stale.css"',
    'rel="stylesheet" href="/assets/index-stale.css" href="/assets/index-proof.css"',
    'rel="stylesheet" HREF="/assets/index-proof.css" href="/assets/index-stale.css"',
    'rel="stylesheet" href="/assets/index-stale.css" HrEf="/assets/index-proof.css"',
  ];
  for (const attributes of duplicateAttributes) {
    const content = `<!-- Unicode offset: 😀 Ж --> <link ${attributes}>`;
    expect(() => assertBuiltCssEntry(html(content), 'index-proof.css')).toThrow('Duplicate attributes on an HTML link');
    rejected.push(content);
  }
  for (const neighbor of [entry, '<link rel="preload" href="/assets/index-proof.css">',
    '<link rel="stylesheet" href="/assets/index-stale.css">']) {
    expect(() => assertBuiltCssEntry(html(entry + neighbor), 'index-proof.css')).toThrow('Built frontend index must reference');
    rejected.push(entry + neighbor);
  }
  const positive = html(`<!-- Unicode offset: 😀 Ж -->${entry}${inert.slice(0, 7).join('')}`);
  expect(() => assertBuiltCssEntry(positive, 'index-proof.css')).not.toThrow();
  expect(() => assertBuiltCssEntry(html(`${entry}<template><link rel="preload" rel="stylesheet" href="/assets/index-proof.css"></template>`), 'index-proof.css')).not.toThrow();
  expect(Object.prototype.hasOwnProperty.call(globalThis, sentinel)).toBe(false);
  await attachCompatibility(testInfo, 'css-document-entry-controls', {
    rejected, positive, scriptSentinelAbsent: !Object.prototype.hasOwnProperty.call(globalThis, sentinel),
    scope: 'Parsed document entry membership only; no CSS fetch, cascade or visual claim',
  });
  await showCompatibilitySpecimens(page, new URL(baseURL ?? '').origin);
  // The guard consumes generated CSS source, not browser CSSOM serialization.
  const origin = new URL(baseURL ?? '').origin;
  const productionCss = page.locator('head link[rel="stylesheet"][href^="/assets/index-"]');
  let css: string;
  let source: { kind: 'production' | 'dev'; location: string; sha256: string };
  if (await productionCss.count() > 0) {
    await expect(productionCss).toHaveCount(1);
    const href = await productionCss.getAttribute('href');
    if (href === null) throw new Error('Production stylesheet href is missing');
    expect(href).toMatch(/^\/assets\/index-[A-Za-z0-9_-]+\.css$/);
    const url = new URL(href, origin);
    expect(url.origin).toBe(origin);
    const response = await page.request.get(url.href, { maxRedirects: 0 });
    try {
      expect(response.status()).toBe(200);
      expect(response.url()).toBe(url.href);
      expect(response.headers()['content-type']).toMatch(/^text\/css(?:;|$)/);
      const bytes = await response.body();
      const file = resolve('dist', url.pathname.slice(1));
      const stat = lstatSync(file);
      expect(stat.isFile() && !stat.isSymbolicLink()).toBe(true);
      const digest = createHash('sha256').update(bytes).digest('hex');
      expect(digest).toBe(createHash('sha256').update(readFileSync(file)).digest('hex'));
      css = bytes.toString('utf8');
      source = { kind: 'production', location: url.href, sha256: digest };
    } finally {
      await response.dispose();
    }
  } else {
    const devCss = page.locator('head style[data-vite-dev-id$="/src/index.css"]');
    await expect(devCss).toHaveCount(1);
    const id = await devCss.getAttribute('data-vite-dev-id');
    expect(id).toBe(resolve('src/index.css').replaceAll('\\', '/'));
    const text = await devCss.textContent();
    if (text === null || id === null) throw new Error('Current Vite source stylesheet is missing');
    css = text;
    source = { kind: 'dev', location: id, sha256: createHash('sha256').update(css).digest('hex') };
  }
  const cssom = await page.evaluate(() => Array.from(document.styleSheets).flatMap((sheet) =>
    Array.from(sheet.cssRules).map((rule) => rule.cssText)).join('\n'));
  await attachCompatibility(testInfo, 'css-raw-source', { source, css, cssom,
    cssomSha256: createHash('sha256').update(cssom).digest('hex') });
  assertTailwindUtilities(css);
  const negative = postcss.parse(css);
  let removed = 0;
  negative.walkRules((rule) => {
    if (rule.selector === '.grid') { rule.remove(); removed += 1; }
  });
  expect(removed).toBeGreaterThan(0);
  await attachCompatibility(testInfo, 'css-selector-negative', { removed,
    positiveSha256: createHash('sha256').update(css).digest('hex'),
    negativeSha256: createHash('sha256').update(negative.toString()).digest('hex') });
  expect(() => assertTailwindUtilities(negative.toString()))
    .toThrow('Built CSS bundle is missing Tailwind selectors: .grid');
});


for (const width of [320, 768, 1440] as const) {
  test(`Home selection keeps actual bounded controls at ${width}px`, async ({ page, baseURL, browserName, browser }, testInfo) => {
    const origin = new URL(baseURL ?? '').origin;
    const sessionCalls = await stubProSession(page, origin);
    await page.setViewportSize({ width, height: width === 320 ? 900 : 1000 });
    await page.goto('/app');
    const heading = page.getByRole('heading', { level: 1, name: 'Turn a check-in into practical meal decisions.' });
    const choice = page.getByRole('button', { name: /Balanced week/ });
    const card = page.getByTestId('planning-intent-selector');
    const before = { heading: await readCompatibilityStyle(heading), card: await readCompatibilityStyle(card),
      choice: await readCompatibilityStyle(choice) };
    await choice.click();
    await expect(choice).toBeFocused();
    await expect(choice).toHaveAttribute('aria-pressed', 'true');
    // Move from the verified real selected control through native Tab and back;
    // assert both actual neighbors rather than assuming a roundtrip succeeded.
    await page.keyboard.press('Tab');
    const neighbor = page.getByRole('button', { name: /Less food decision fatigue/ });
    await attachCompatibility(testInfo, 'home-forward-intermediate', await readCompatibilityStyle(neighbor));
    await expect(neighbor).toBeFocused();
    await page.keyboard.press('Shift+Tab');
    const focused = await readCompatibilityStyle(choice);
    await attachCompatibility(testInfo, 'home-keyboard', { width, browserName, version: browser.version(),
      before, focused, sessionCalls: sessionCalls() });
    await expect(choice).toBeFocused();
    const homeText = await readCompatibilityStyle(page.locator('#planning-intent-heading'));
    expect(homeText.classes.split(/\s+/)).toContain('text-white');
    expect(homeText.style.color).toBe(homeText.expectedFocus.surface);
    await attachCompatibility(testInfo, 'home-text-white', homeText);
    expectVisibleCompatibilityOutline(focused);
    await choice.hover();
    await attachCompatibility(testInfo, 'home-hover', await readCompatibilityStyle(choice));
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  });
}

for (const route of ['/plate', '/progress'] as const) {
  for (const width of [320, 1440] as const) {
    test(`${route} compares actual protected page CSS at ${width}px`, async ({ page, baseURL, browserName, browser }, testInfo) => {
      const origin = new URL(baseURL ?? '').origin;
      const sessionCalls = await stubProSession(page, origin);
      const apiRequests: Array<{ url: string; method: string }> = [];
      page.on('request', (request) => {
        if (['fetch', 'xhr', 'eventsource', 'websocket'].includes(request.resourceType())) {
          apiRequests.push({ url: request.url(), method: request.method() });
        }
      });
      await page.setViewportSize({ width, height: width === 320 ? 900 : 1000 });
      await page.goto(route);
      const heading = page.getByRole('heading', { level: 1, name: route === '/plate' ? 'Your Plate' : 'Progress' });
      await expect(heading).toBeVisible();
      await expect(page.locator('#api-key-input')).toHaveCount(0);
      await expect(page.getByRole('tablist', { name: 'Main tabs' })).toBeVisible();
      const captureProtectedTargets = async (radio?: Locator) => {
        const h2 = page.getByRole('heading', { level: 2,
          name: route === '/plate' ? 'Premium Nutrition Controls' : 'Progress Tracking' });
        const setup = page.getByRole('link', { name: 'Configure Setup' });
        const charts = page.locator('#progress-charts');
        // The frozen BASE selectors select the actual Card owners. Their parents,
        // controls and child rectangles retain padding, gaps and responsive stacks.
        const targets: Record<string, Locator> = route === '/plate'
          ? { h1: heading, h2, setup, content: h2.locator('..'), card: h2.locator('../..'),
            controls: setup.locator('..'), stack: h2.locator('../../..') }
          : { h1: heading, h2, charts, card: charts.locator('../..'), content: charts.locator('..'),
            stack: charts.locator('../../..'), responsiveStack: heading.locator('../..'),
            controls: page.getByRole('radiogroup', { name: 'Progress time range filter' }) };
        if (radio) targets.radio = radio;
        const selected: Record<string, Awaited<ReturnType<typeof readCompatibilityStyle>>> = {};
        for (const [name, locator] of Object.entries(targets)) selected[name] = await readCompatibilityStyle(locator);
        return selected;
      };
      const states: Array<{ label: string; selected: Awaited<ReturnType<typeof captureProtectedTargets>> }> = [];
      if (route === '/plate') {
        await expect(page.getByRole('heading', { name: 'Premium Nutrition Controls' })).toBeVisible();
        await expect(page.getByRole('link', { name: 'Configure Setup' })).toHaveAttribute('href', '/setup');
        const selected = await captureProtectedTargets();
        states.push({ label: 'actual-plate', selected });
        await attachCompatibility(testInfo, 'protected-plate-targets', { viewport: page.viewportSize(), selected });
      } else {
        await expect(page.locator('#progress-charts')).toBeVisible();
        await expect(page.getByRole('heading', { name: 'Progress Tracking' })).toBeVisible();
        await expect(page.getByText('No progress data yet', { exact: true })).toBeVisible();
        for (const [label, description] of [['WEEK', 'Last week'], ['MONTH', 'Last month'], ['QUARTER', 'Last quarter']] as const) {
          await page.getByRole('radio', { name: label, exact: true }).click();
          await expect(page.getByRole('radio', { name: label, exact: true })).toBeChecked();
          await expect(page.getByText(`Viewing: ${description}`, { exact: true })).toBeVisible();
          const selected = await captureProtectedTargets(page.getByRole('radio', { name: label, exact: true }));
          states.push({ label, selected });
          await attachCompatibility(testInfo, `protected-progress-${label}`, { viewport: page.viewportSize(), selected });
        }
      }
      const observation = await readCompatibilityStyle(heading);
      await attachCompatibility(testInfo, 'protected-page', { route, width, browserName, version: browser.version(),
        sessionCalls: sessionCalls(), viewport: page.viewportSize(), heading: observation, states, apiRequests });
      expect(sessionCalls()).toBeGreaterThan(0);
      expect(observation.style['font-size']).toBe(width === 320 ? '36px' : '48px');
      expect(observation.style['font-weight']).toBe('700');
      expect(apiRequests.every((request) => request.url === `${origin}/api/v1/pro/session` && request.method === 'GET')).toBe(true);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    });
  }
}

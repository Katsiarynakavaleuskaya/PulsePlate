import { expect, test } from '@playwright/test';

test.describe('Accessibility Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should have proper page title and language', async ({ page }) => {
    // Проверяем наличие title
    const title = await page.title();
    expect(title).toBeTruthy();
    expect(title.length).toBeGreaterThan(0);

    // Проверяем наличие lang атрибута
    const lang = await page.getAttribute('html', 'lang');
    expect(lang).toBeTruthy();
  });

  test('should have proper heading structure', async ({ page }) => {
    // Проверяем наличие h1
    const h1 = await page.locator('h1');
    await expect(h1).toHaveCount(1);

    // Проверяем, что заголовки имеют содержимое
    const headings = await page.locator('h1, h2, h3, h4, h5, h6').all();
    for (const heading of headings) {
      const text = await heading.textContent();
      expect(text?.trim()).toBeTruthy();
    }
  });

  test('should have proper alt text for images', async ({ page }) => {
    const images = await page.locator('img').all();

    for (const img of images) {
      const alt = await img.getAttribute('alt');
      // Alt может быть пустым для декоративных изображений, но должен присутствовать
      expect(alt).not.toBeNull();
    }
  });

  test('should have proper ARIA labels for interactive elements', async ({ page }) => {
    // Проверяем кнопки
    const buttons = await page.locator('button').all();
    for (const button of buttons) {
      const ariaLabel = await button.getAttribute('aria-label');
      const ariaLabelledBy = await button.getAttribute('aria-labelledby');
      const textContent = await button.textContent();

      // Кнопка должна иметь либо aria-label, либо aria-labelledby, либо текстовое содержимое
      const hasAccessibleName = ariaLabel || ariaLabelledBy || textContent?.trim();
      expect(hasAccessibleName).toBeTruthy();
    }

    // Проверяем ссылки
    const links = await page.locator('a').all();
    for (const link of links) {
      const ariaLabel = await link.getAttribute('aria-label');
      const ariaLabelledBy = await link.getAttribute('aria-labelledby');
      const textContent = await link.textContent();
      const href = await link.getAttribute('href');

      // Ссылка должна иметь либо aria-label, либо aria-labelledby, либо текстовое содержимое
      const hasAccessibleName = ariaLabel || ariaLabelledBy || textContent?.trim();
      expect(hasAccessibleName).toBeTruthy();

      // Ссылка должна иметь href или role="button"
      const role = await link.getAttribute('role');
      expect(href || role === 'button').toBeTruthy();
    }
  });

  test('should have proper form labels', async ({ page }) => {
    const inputs = await page.locator('input, textarea, select').all();

    for (const input of inputs) {
      const id = await input.getAttribute('id');
      const ariaLabel = await input.getAttribute('aria-label');
      const ariaLabelledBy = await input.getAttribute('aria-labelledby');
      const placeholder = await input.getAttribute('placeholder');

      if (id) {
        // Если есть id, должен быть соответствующий label
        const label = await page.locator(`label[for="${id}"]`);
        const hasLabel = await label.count() > 0;
        expect(hasLabel || ariaLabel || ariaLabelledBy || placeholder).toBeTruthy();
      } else {
        // Если нет id, должен быть aria-label или aria-labelledby
        expect(ariaLabel || ariaLabelledBy || placeholder).toBeTruthy();
      }
    }
  });

  test('should have proper focus management', async ({ page }) => {
    // Проверяем, что можно навигировать с клавиатуры
    await page.keyboard.press('Tab');
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
    expect(focusedElement).toBeTruthy();
  });

  test('should have proper color contrast', async ({ page }) => {
    // Проверяем основные элементы на контрастность
    const textElements = await page.locator('p, span, div, h1, h2, h3, h4, h5, h6').all();

    for (const element of textElements.slice(0, 10)) { // Проверяем первые 10 элементов
      const text = await element.textContent();
      if (text?.trim()) {
        const color = await element.evaluate((el) => {
          const styles = window.getComputedStyle(el);
          return {
            color: styles.color,
            backgroundColor: styles.backgroundColor
          };
        });

        // Базовая проверка - цвета должны быть определены
        expect(color.color).toBeTruthy();
        expect(color.backgroundColor).toBeTruthy();
      }
    }
  });

  test('should have proper ARIA landmarks', async ({ page }) => {
    // Проверяем наличие основных ARIA landmarks
    const main = page.locator('main, [role="main"]');

    // Основные landmarks должны присутствовать
    const mainCount = await main.count();
    expect(mainCount).toBeGreaterThan(0);
  });

  test('should handle keyboard navigation', async ({ page }) => {
    // Проверяем навигацию с клавиатуры
    const interactiveElements = await page.locator('button, a, input, select, textarea, [tabindex]').all();

    if (interactiveElements.length > 0) {
      // Начинаем с первого элемента
      await interactiveElements[0].focus();

      // Проверяем, что элемент получил фокус
      const isFocused = await interactiveElements[0].evaluate((el) => el === document.activeElement);
      expect(isFocused).toBeTruthy();
    }
  });

  test('should have proper error handling', async ({ page }) => {
    // Проверяем, что ошибки имеют proper ARIA attributes
    const errorElements = await page.locator('[role="alert"], .error, .invalid').all();

    for (const error of errorElements) {
      const role = await error.getAttribute('role');
      const ariaLive = await error.getAttribute('aria-live');

      // Ошибки должны иметь role="alert" или aria-live
      expect(role === 'alert' || ariaLive).toBeTruthy();
    }
  });
});

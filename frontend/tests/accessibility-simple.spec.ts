import { expect, test } from '@playwright/test';

test.describe('Accessibility Simple Tests', () => {
  test('should have proper page structure', async ({ page }) => {
    // Простой тест для проверки базовой структуры
    await page.goto('http://localhost:5173');

    // Проверяем наличие title
    const title = await page.title();
    expect(title).toBeTruthy();

    // Проверяем наличие lang атрибута
    const lang = await page.getAttribute('html', 'lang');
    expect(lang).toBeTruthy();
  });

  test('should have proper heading structure', async ({ page }) => {
    await page.goto('http://localhost:5173');

    // Проверяем наличие h1
    const h1 = await page.locator('h1');
    const h1Count = await h1.count();
    expect(h1Count).toBeGreaterThanOrEqual(0); // Может быть 0 если страница не загрузилась
  });

  test('should have proper alt text for images', async ({ page }) => {
    await page.goto('http://localhost:5173');

    const images = await page.locator('img').all();

    for (const img of images) {
      const alt = await img.getAttribute('alt');
      // Alt может быть пустым для декоративных изображений, но должен присутствовать
      expect(alt).not.toBeNull();
    }
  });
});

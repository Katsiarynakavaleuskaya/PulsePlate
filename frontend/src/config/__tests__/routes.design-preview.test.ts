import { describe, expect, it } from 'vitest';
import { routes } from '../routes';

describe('design preview routes', (): void => {
  it('registers the marketing page as a hidden public route', (): void => {
    expect(routes).toContainEqual(
      expect.objectContaining({
        path: '/marketing',
        requiresAuth: false,
        hideTabBar: true,
      })
    );
  });

  it('registers the design system preview as a hidden public route', (): void => {
    expect(routes).toContainEqual(
      expect.objectContaining({
        path: '/design-system',
        requiresAuth: false,
        hideTabBar: true,
      })
    );
  });

  it('registers the welcome gate preview as a hidden public route', () => {
    expect(routes).toContainEqual(
      expect.objectContaining({
        path: '/welcome-gate-v1',
        requiresAuth: false,
        hideTabBar: true,
      })
    );
  });
});

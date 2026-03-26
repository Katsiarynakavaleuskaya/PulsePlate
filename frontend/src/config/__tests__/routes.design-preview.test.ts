import { describe, expect, it } from 'vitest';
import { routes } from '../routes';

describe('design preview routes', () => {
  it('registers the design system preview as a hidden public route', () => {
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

import { describe, expect, it } from 'vitest';
import { routes } from '../routes';

describe('design preview routes', (): void => {
  it('registers the design system preview as a hidden public route', (): void => {
    expect(routes).toContainEqual(
      expect.objectContaining({
        path: '/design-system',
        requiresAuth: false,
        hideTabBar: true,
      })
    );
  });
});

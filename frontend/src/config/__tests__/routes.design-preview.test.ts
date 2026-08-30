import { describe, expect, it } from 'vitest';
import { routes } from '../routes';

describe('design preview routes', (): void => {
  it('registers the public root as a hidden launch route', (): void => {
    expect(routes).toContainEqual(
      expect.objectContaining({
        path: '/',
        label: 'Launch',
        requiresAuth: false,
        hideTabBar: true,
      })
    );
  });

  it('preserves the app home as a tabbed route', (): void => {
    expect(routes).toContainEqual(
      expect.objectContaining({
        path: '/app',
        label: 'Home',
        requiresAuth: false,
      })
    );
  });

  it('registers the marketing page as a hidden public route', (): void => {
    expect(routes).toContainEqual(
      expect.objectContaining({
        path: '/marketing',
        requiresAuth: false,
        hideTabBar: true,
      })
    );
  });

  it('binds the root and marketing URLs to the same page component', (): void => {
    const rootRoute = routes.find((route) => route.path === '/');
    const marketingRoute = routes.find((route) => route.path === '/marketing');

    expect(rootRoute).toBeDefined();
    expect(marketingRoute).toBeDefined();
    expect(rootRoute?.component).toBe(marketingRoute?.component);
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

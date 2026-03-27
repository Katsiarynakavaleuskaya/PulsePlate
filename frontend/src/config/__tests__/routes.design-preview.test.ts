import { describe, expect, it } from 'vitest';
import { routes } from '../routes';
import { WELCOME_GATE_V1_ROUTE_PATH } from '../../pages/Onboarding/welcomeGateV1Policy';

const PREVIEW_ONLY_ROUTE_PATHS = ['/design-system', WELCOME_GATE_V1_ROUTE_PATH] as const;

describe('design preview routes', (): void => {
  it('registers the design system preview as a hidden public route', (): void => {
    expect(routes).toContainEqual(
      expect.objectContaining({
        path: '/design-system',
        requiresAuth: false,
        hideTabBar: true,
        previewOnly: true,
      })
    );
  });

  it('registers the welcome gate preview as a hidden public route', () => {
    expect(routes).toContainEqual(
      expect.objectContaining({
        path: WELCOME_GATE_V1_ROUTE_PATH,
        requiresAuth: false,
        hideTabBar: true,
        previewOnly: true,
      })
    );
  });

  it('marks only the intended routes as preview-only', (): void => {
    const previewOnlyPaths = routes
      .filter(route => route.previewOnly)
      .map(route => route.path)
      .sort();

    expect(previewOnlyPaths).toEqual([...PREVIEW_ONLY_ROUTE_PATHS].sort());
  });
});

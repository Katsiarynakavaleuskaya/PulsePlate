import { createPremiumEndpoint, type TargetsRequest, type TargetsApiResponse } from './types';

/**
 * Deprecated premium client → canonical PRO route.
 * Kept under premium/* during migration.
 */
export const getTargets = createPremiumEndpoint<TargetsRequest, TargetsApiResponse>(
  '/api/v1/pro/nutrition/targets'
);

export type { TargetsRequest, TargetsApiResponse } from './types';

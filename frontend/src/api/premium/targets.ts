import { createPremiumEndpoint } from './types';
import type { TargetsRequest, TargetsApiResponse } from './types';

export const getTargets = createPremiumEndpoint<TargetsRequest, TargetsApiResponse>(
  '/api/v1/pro/nutrition/targets'
);

export type { TargetsRequest, TargetsApiResponse } from './types';

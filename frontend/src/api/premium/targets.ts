import { createPremiumEndpoint, type TargetsRequest, type TargetsApiResponse } from './types';

export const getTargets = createPremiumEndpoint<TargetsRequest, TargetsApiResponse>('/api/v1/premium/targets');

export type { TargetsRequest, TargetsApiResponse } from './types';

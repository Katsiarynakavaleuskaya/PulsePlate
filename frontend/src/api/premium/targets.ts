import { api } from '../client';
import type { PremiumRequestOptions, TargetsRequest, TargetsApiResponse } from './types';

export const getTargets = (body: TargetsRequest, options?: PremiumRequestOptions) =>
  api<TargetsApiResponse>(
    '/api/v1/premium/targets',
    { method: 'POST', body: JSON.stringify(body), signal: options?.signal },
    options?.navigate,
    true,
  );

export type { TargetsRequest, TargetsApiResponse } from './types';

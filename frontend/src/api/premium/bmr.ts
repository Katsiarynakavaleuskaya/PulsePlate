import { api } from '../client';
import type { PremiumRequestOptions, BmrRequest, BmrApiResponse } from './types';

export const getBmr = (body: BmrRequest, options?: PremiumRequestOptions) =>
  api<BmrApiResponse>(
    '/api/v1/premium/bmr',
    { method: 'POST', body: JSON.stringify(body), signal: options?.signal },
    options?.navigate,
    true,
  );

export type { BmrRequest, BmrApiResponse } from './types';

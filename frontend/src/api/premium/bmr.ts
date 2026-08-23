import { createPremiumEndpoint } from './types';
import type { BmrRequest, BmrApiResponse } from './types';

export const getBmr = createPremiumEndpoint<BmrRequest, BmrApiResponse>(
  '/api/v1/pro/nutrition/bmr'
);

export type { BmrRequest, BmrApiResponse } from './types';

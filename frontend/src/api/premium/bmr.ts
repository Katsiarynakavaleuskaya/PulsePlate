import { createPremiumEndpoint, type BmrRequest, type BmrApiResponse } from './types';

export const getBmr = createPremiumEndpoint<BmrRequest, BmrApiResponse>('/api/v1/premium/bmr');

export type { BmrRequest, BmrApiResponse } from './types';

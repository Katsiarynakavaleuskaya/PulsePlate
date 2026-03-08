import { createPremiumEndpoint } from './types';
import type { components } from '../schema';

export type CbtInsightRequest = components['schemas']['CBTInsightRequest'];
export type CbtInsightResponse = components['schemas']['CBTInsightResponse'];

export const getCbtInsight = createPremiumEndpoint<CbtInsightRequest, CbtInsightResponse>(
  '/api/v1/pro/cbt/insight'
);

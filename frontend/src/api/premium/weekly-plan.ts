import { createPremiumEndpoint } from './types';
import type { TargetsRequest } from './types';
import type { components } from '../schema';

// Use the WeeklyMenuResponse from OpenAPI schema
export type WeeklyMenuResponse = components['schemas']['WeeklyMenuResponse'];

export const getWeeklyPlan = createPremiumEndpoint<TargetsRequest, WeeklyMenuResponse>('/api/v1/premium/plan/week');

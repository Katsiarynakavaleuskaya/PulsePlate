import { createPremiumEndpoint } from './types';
import type { components } from '../schema';

// Use canonical OpenAPI types from the public PRO contract.
export type WeekPlanRequest = components['schemas']['ProWeekPlanRequest'];
export type WeeklyMenuResponse = components['schemas']['WeeklyMealPlanResponse'];

/**
 * Generate weekly meal plan (PRO tier).
 *
 * Migrated from deprecated /api/v1/premium/plan/week to canonical /api/v1/pro/meal/weekly.
 * Uses canonical OpenAPI request/response types from /api/v1/pro/meal/weekly.
 */
export const getWeeklyPlan = createPremiumEndpoint<WeekPlanRequest, WeeklyMenuResponse>(
  '/api/v1/pro/meal/weekly'  // ✅ Canonical endpoint
);

import { createPremiumEndpoint } from './types';
import type { components } from '../schema';

// Use OpenAPI types (canonical)
export type WeekPlanRequest = components['schemas']['WeekPlanRequest'];
export type WeeklyMenuResponse = components['schemas']['WeeklyMenuResponse'];

/**
 * Generate weekly meal plan (PRO tier).
 *
 * Migrated from deprecated /api/v1/premium/plan/week to canonical /api/v1/pro/meal/weekly.
 * Uses OpenAPI WeekPlanRequest and WeeklyMenuResponse types.
 */
export const getWeeklyPlan = createPremiumEndpoint<WeekPlanRequest, WeeklyMenuResponse>(
  '/api/v1/pro/meal/weekly'  // ✅ Canonical endpoint
);

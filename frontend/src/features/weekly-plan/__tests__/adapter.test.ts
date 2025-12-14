/**
 * @vitest-environment jsdom
 */

import { describe, it, expect } from 'vitest';
import { normalizeWeekPlan } from '../model/adapter';
import type { RawWeekPlanResponse } from '../model/types';

describe('normalizeWeekPlan', () => {
  it('should normalize complete valid response', () => {
    const raw: RawWeekPlanResponse = {
      daily_menus: [
        {
          day: 1,
          meals: [
            {
              meal_type: 'breakfast',
              recipes: [
                { id: 'r1', name: 'Oatmeal', portions: 1.5 },
                { id: 'r2', name: 'Berries', portions: 1 },
              ],
              totals: { kcal: 450, protein_g: 15, fat_g: 10, carbs_g: 70 },
            },
          ],
          daily_totals: { kcal: 2000, protein_g: 100, fat_g: 70, carbs_g: 250 },
        },
      ],
      weekly_coverage: { protein: 98.5, iron: 95.1, vitamin_c: 120.2, calcium: 88.0 },
      shopping_list: {},
      total_cost: 150.0,
      adherence_score: 0.95,
    };

    const result = normalizeWeekPlan(raw);

    expect(result.days).toHaveLength(1);
    expect(result.days[0].day).toBe(1);
    expect(result.days[0].dayName).toBe('Monday');
    expect(result.days[0].meals).toHaveLength(1);
    expect(result.days[0].meals[0].meal_type).toBe('breakfast');
    expect(result.days[0].meals[0].recipes).toHaveLength(2);
    expect(result.weekly_coverage.protein).toBe(98.5);
    expect(result.metrics.total_cost).toBe(150.0);
    expect(result.metrics.adherence_score).toBe(0.95);
    expect(result.meta.total_days).toBe(1);
    expect(result.meta.has_incomplete_data).toBe(false);
  });

  it('should handle missing daily_menus with empty array', () => {
    const raw: RawWeekPlanResponse = {
      daily_menus: [],
      weekly_coverage: {},
      shopping_list: {},
      total_cost: 0,
      adherence_score: 0,
    };

    const result = normalizeWeekPlan(raw);

    expect(result.days).toHaveLength(0);
    expect(result.meta.total_days).toBe(0);
  });

  it('should provide defaults for malformed day data', () => {
    const raw: RawWeekPlanResponse = {
      daily_menus: [null as unknown as Record<string, unknown>],
      weekly_coverage: {},
      shopping_list: {},
      total_cost: 0,
      adherence_score: 0,
    };

    const result = normalizeWeekPlan(raw);

    expect(result.days).toHaveLength(1);
    expect(result.days[0].day).toBe(1);
    expect(result.days[0].dayName).toBe('Monday');
    expect(result.days[0].meals).toEqual([]);
    expect(result.meta.has_incomplete_data).toBe(true);
  });

  it('should calculate daily totals from meals if not provided', () => {
    const raw: RawWeekPlanResponse = {
      daily_menus: [
        {
          day: 1,
          meals: [
            {
              meal_type: 'breakfast',
              recipes: [],
              totals: { kcal: 500, protein_g: 20, fat_g: 15, carbs_g: 60, fiber_g: 4 },
            },
            {
              meal_type: 'lunch',
              recipes: [],
              totals: { kcal: 700, protein_g: 35, fat_g: 25, carbs_g: 80, fiber_g: 9 },
            },
          ],
          // No daily_totals provided
        },
      ],
      weekly_coverage: {},
      shopping_list: {},
      total_cost: 0,
      adherence_score: 0,
    };

    const result = normalizeWeekPlan(raw);

    expect(result.days[0].daily_totals.kcal).toBe(1200);
    expect(result.days[0].daily_totals.protein_g).toBe(55);
    expect(result.days[0].daily_totals.fat_g).toBe(40);
    expect(result.days[0].daily_totals.carbs_g).toBe(140);
    expect(result.days[0].daily_totals.fiber_g).toBe(13);
  });

  it('should use daily_totals.fiber_g when provided (overrides calculated fallback)', () => {
    const raw: RawWeekPlanResponse = {
      daily_menus: [
        {
          day: 1,
          meals: [
            {
              meal_type: 'breakfast',
              recipes: [],
              totals: { kcal: 200, protein_g: 10, fat_g: 5, carbs_g: 30, fiber_g: 4 },
            },
            {
              meal_type: 'lunch',
              recipes: [],
              totals: { kcal: 400, protein_g: 25, fat_g: 15, carbs_g: 45, fiber_g: 9 },
            },
          ],
          daily_totals: {
            kcal: 600,
            protein_g: 35,
            fat_g: 20,
            carbs_g: 75,
            fiber_g: 99, // Explicit value overrides calculated (4 + 9 = 13)
          },
        },
      ],
      weekly_coverage: {},
      shopping_list: {},
      total_cost: 0,
      adherence_score: 0,
    };

    const result = normalizeWeekPlan(raw);

    expect(result.days[0].daily_totals.fiber_g).toBe(99);
  });

  it('should handle missing meal recipes gracefully', () => {
    const raw: RawWeekPlanResponse = {
      daily_menus: [
        {
          day: 1,
          meals: [
            {
              meal_type: 'breakfast',
              // No recipes
              totals: { kcal: 450 },
            },
          ],
          daily_totals: { kcal: 450, protein_g: 0, fat_g: 0, carbs_g: 0 },
        },
      ],
      weekly_coverage: {},
      shopping_list: {},
      total_cost: 0,
      adherence_score: 0,
    };

    const result = normalizeWeekPlan(raw);

    expect(result.days[0].meals[0].recipes).toEqual([]);
  });

  it('should assign correct day names based on day number', () => {
    const raw: RawWeekPlanResponse = {
      daily_menus: [
        { day: 1, meals: [], daily_totals: { kcal: 0, protein_g: 0, fat_g: 0, carbs_g: 0 } },
        { day: 2, meals: [], daily_totals: { kcal: 0, protein_g: 0, fat_g: 0, carbs_g: 0 } },
        { day: 7, meals: [], daily_totals: { kcal: 0, protein_g: 0, fat_g: 0, carbs_g: 0 } },
      ],
      weekly_coverage: {},
      shopping_list: {},
      total_cost: 0,
      adherence_score: 0,
    };

    const result = normalizeWeekPlan(raw);

    expect(result.days[0].dayName).toBe('Monday');
    expect(result.days[1].dayName).toBe('Tuesday');
    expect(result.days[2].dayName).toBe('Sunday');
  });

  it('should normalize weekly coverage with defaults', () => {
    const raw: RawWeekPlanResponse = {
      daily_menus: [],
      weekly_coverage: { protein: 100, iron: 90 }, // Missing vitamin_c, calcium
      shopping_list: {},
      total_cost: 0,
      adherence_score: 0,
    };

    const result = normalizeWeekPlan(raw);

    expect(result.weekly_coverage.protein).toBe(100);
    expect(result.weekly_coverage.iron).toBe(90);
    expect(result.weekly_coverage.vitamin_c).toBe(0);
    expect(result.weekly_coverage.calcium).toBe(0);
  });

  it('should preserve extra coverage fields', () => {
    const raw: RawWeekPlanResponse = {
      daily_menus: [],
      weekly_coverage: {
        protein: 100,
        iron: 90,
        vitamin_c: 120,
        calcium: 85,
        vitamin_d: 110,
        magnesium: 95,
      },
      shopping_list: {},
      total_cost: 0,
      adherence_score: 0,
    };

    const result = normalizeWeekPlan(raw);

    expect(result.weekly_coverage.vitamin_d).toBe(110);
    expect(result.weekly_coverage.magnesium).toBe(95);
  });

  it('should handle NaN values by falling back to defaults', () => {
    const raw: RawWeekPlanResponse = {
      daily_menus: [],
      weekly_coverage: {},
      shopping_list: {},
      total_cost: NaN,
      adherence_score: NaN,
    };

    const result = normalizeWeekPlan(raw);

    expect(result.metrics.total_cost).toBe(0);
    expect(result.metrics.adherence_score).toBe(0);
  });
});

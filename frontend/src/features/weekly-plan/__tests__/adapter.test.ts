/**
 * @vitest-environment jsdom
 */

import { describe, it, expect } from 'vitest';
import { normalizeWeekPlan } from '../model/adapter';
import type { RawWeekPlanResponse } from '../model/types';

function createRawWeekPlan(
  overrides: Partial<RawWeekPlanResponse> = {}
): RawWeekPlanResponse {
  return {
    daily_menus: [
      {
        coverage: { protein: 102, iron: 91 },
        kcal: 1860,
        macros: { protein_g: 112, carbs_g: 175, fat_g: 63 },
        meals: [
          {
            title: 'Oat bowl',
            title_translated: 'Oat bowl',
            grams: { oats: 80, berries: 60 },
            kcal: 430,
            macros: { protein_g: 16, carbs_g: 62, fat_g: 11 },
            micros: { iron_mg: 3.2 },
            price_est: 3.75,
          },
        ],
        micros: { iron_mg: 11.2, vitamin_c_mg: 84 },
        tips: ['Rotate vegetables'],
        total_cost: 18.5,
      },
    ],
    weekly_coverage: {
      protein: 98.5,
      iron: 95.1,
      vitamin_c: 120.2,
      calcium: 88,
    },
    shopping_list: { oats: 560, berries: 420 },
    total_cost: 150,
    adherence_score: 0.95,
    ...overrides,
  };
}

describe('normalizeWeekPlan', () => {
  it('should normalize complete valid response', () => {
    const result = normalizeWeekPlan(createRawWeekPlan());

    expect(result.days).toHaveLength(1);
    expect(result.days[0].day).toBe(1);
    expect(result.days[0].dayName).toBe('Monday');
    expect(result.days[0].meals).toHaveLength(1);
    expect(result.days[0].meals[0].title).toBe('Oat bowl');
    expect(result.days[0].meals[0].price_est).toBe(3.75);
    expect(result.weekly_coverage.protein).toBe(98.5);
    expect(result.shopping_list.oats).toBe(560);
    expect(result.metrics.total_cost).toBe(150);
    expect(result.metrics.adherence_score).toBe(0.95);
    expect(result.meta.total_days).toBe(1);
    expect(result.meta.has_incomplete_data).toBe(false);
  });

  it('should keep empty daily_menus as empty array', () => {
    const result = normalizeWeekPlan(createRawWeekPlan({ daily_menus: [] }));

    expect(result.days).toHaveLength(0);
    expect(result.meta.total_days).toBe(0);
  });

  it('should return safe defaults for malformed root payloads', () => {
    const malformedPayloads = [
      null,
      42,
      'broken-root',
    ] as unknown as RawWeekPlanResponse[];

    malformedPayloads.forEach((payload) => {
      const result = normalizeWeekPlan(payload);

      expect(result.days).toEqual([]);
      expect(result.weekly_coverage).toEqual({});
      expect(result.shopping_list).toEqual({});
      expect(result.metrics.total_cost).toBe(0);
      expect(result.metrics.adherence_score).toBe(0);
      expect(result.meta.total_days).toBe(0);
      expect(result.meta.has_incomplete_data).toBe(true);
    });
  });

  it('should preserve backend coverage values without frontend clamping', () => {
    const result = normalizeWeekPlan(
      createRawWeekPlan({
        weekly_coverage: {
          protein: 450,
          iron: -10,
          vitamin_c: 125,
          calcium: 85,
          magnesium: 330,
        },
      })
    );

    expect(result.weekly_coverage.protein).toBe(450);
    expect(result.weekly_coverage.iron).toBe(-10);
    expect(result.weekly_coverage.magnesium).toBe(330);
  });

  it('should ignore invalid numeric map values', () => {
    const result = normalizeWeekPlan(
      createRawWeekPlan({
        shopping_list: {
          apples: 5,
          bad: Number.NaN,
        },
      })
    );

    expect(result.shopping_list.apples).toBe(5);
    expect(result.shopping_list.bad).toBeUndefined();
  });

  it('should preserve backend adherence score without frontend clamping', () => {
    const result = normalizeWeekPlan(createRawWeekPlan({ adherence_score: 2.5 }));

    expect(result.metrics.adherence_score).toBe(2.5);
  });

  it('should keep meal maps typed and intact', () => {
    const result = normalizeWeekPlan(createRawWeekPlan());
    const meal = result.days[0].meals[0];

    expect(meal.grams.oats).toBe(80);
    expect(meal.macros.protein_g).toBe(16);
    expect(meal.micros.iron_mg).toBe(3.2);
  });

  it('should tolerate malformed day menu entries without crashing', () => {
    const result = normalizeWeekPlan(
      createRawWeekPlan({
        daily_menus: [null as unknown as RawWeekPlanResponse['daily_menus'][number]],
      })
    );

    expect(result.days).toHaveLength(0);
    expect(result.meta.has_incomplete_data).toBe(true);
  });

  it('should preserve original day index after skipping malformed daily menu entries', () => {
    const result = normalizeWeekPlan(
      createRawWeekPlan({
        daily_menus: [
          null as unknown as RawWeekPlanResponse['daily_menus'][number],
          {
            coverage: { protein: 88 },
            kcal: 1740,
            macros: { protein_g: 105, carbs_g: 160, fat_g: 58 },
            meals: [
              {
                title: 'Lunch bowl',
                title_translated: 'Lunch bowl',
                grams: { chicken: 140 },
                kcal: 520,
                macros: { protein_g: 42, carbs_g: 28, fat_g: 14 },
                micros: { iron_mg: 2.1 },
                price_est: 6.25,
              },
            ],
            micros: { iron_mg: 9.5 },
            tips: ['Stay hydrated'],
            total_cost: 21,
          },
        ],
      })
    );

    expect(result.days).toHaveLength(1);
    expect(result.days[0].day).toBe(2);
    expect(result.days[0].dayName).toBe('Tuesday');
    expect(result.meta.has_incomplete_data).toBe(true);
  });

  it('should mark incomplete data when fallbacks or drops happen', () => {
    const result = normalizeWeekPlan(
      createRawWeekPlan({
        daily_menus: [
          {
            coverage: { protein: 102 },
            kcal: 1860,
            macros: { protein_g: 112 },
            meals: [
              {
                title: 'Broken meal',
                title_translated: 42 as unknown as string,
                grams: { oats: 80, bad: Number.NaN },
                kcal: Number.NaN,
                macros: { protein_g: 16 },
                micros: { iron_mg: 3.2 },
                price_est: 'oops' as unknown as number,
              },
              null as unknown as RawWeekPlanResponse['daily_menus'][number]['meals'][number],
            ],
            micros: { iron_mg: 11.2 },
            tips: ['Rotate vegetables', 42 as unknown as string],
            total_cost: 18.5,
          },
        ],
      })
    );

    expect(result.days[0].meals).toHaveLength(1);
    expect(result.meta.has_incomplete_data).toBe(true);
  });
});

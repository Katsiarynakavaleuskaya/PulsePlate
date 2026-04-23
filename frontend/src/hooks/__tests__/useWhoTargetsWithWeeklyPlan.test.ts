import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useWhoTargetsWithWeeklyPlan } from '../useWhoTargetsWithWeeklyPlan';
import type { TargetsApiResponse, TargetsRequest } from '../../api/premium/types';
import type { WeeklyMealPlanResponse } from '../../api/premium/weekly-plan';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string) => fallback || _key,
  }),
}));

vi.mock('../../api/premium', () => ({
  getTargets: vi.fn(),
  getWeeklyPlan: vi.fn(),
}));

import { getTargets, getWeeklyPlan } from '../../api/premium';

const mockGetTargets = vi.mocked(getTargets);
const mockGetWeeklyPlan = vi.mocked(getWeeklyPlan);

const REQUEST: TargetsRequest = {
  sex: 'female',
  age: 29,
  height_cm: 165,
  weight_kg: 61,
  activity: 'moderate',
  goal: 'maintain',
  lang: 'en',
  life_stage: 'adult',
};

const TARGETS_RESPONSE: TargetsApiResponse = {
  kcal_daily: 2000,
  macros: {
    protein_g: 120,
    carbs_g: 210,
    fat_g: 70,
    fiber_g: 28,
  },
  water_ml: 2100,
  priority_micros: {
    iron: 18,
    calcium: 1000,
  },
  activity_weekly: {
    moderate_aerobic_min: 150,
    strength_sessions: 2,
    steps_daily: 8000,
  },
  calculation_date: '2026-03-10T10:00:00Z',
  warnings: [],
};

const WEEKLY_PLAN_RESPONSE: WeeklyMealPlanResponse = {
  daily_menus: [
    {
      kcal: 1800,
      total_cost: 18.5,
      coverage: { protein: 0.92, fiber: 0.8 },
      macros: { protein_g: 110, carbs_g: 180, fat_g: 60 },
      micros: { iron_mg: 12 },
      tips: ['Hydrate'],
      meals: [
        {
          title: 'Chicken bowl',
          title_translated: 'Chicken bowl',
          kcal: 620,
          price_est: 7.25,
          grams: { chicken: 180, rice: 150 },
          macros: { protein_g: 42, carbs_g: 58, fat_g: 14 },
          micros: { iron_mg: 3.4 },
        },
      ],
    },
  ],
  weekly_coverage: { protein: 0.95, fiber: 0.81 },
  shopping_list: { chicken: 1200, rice: 900 },
  total_cost: 72.4,
  adherence_score: 0.88,
};

describe('useWhoTargetsWithWeeklyPlan', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('normalizes weekly plan state before exposing it', async () => {
    mockGetTargets.mockResolvedValue(TARGETS_RESPONSE);
    mockGetWeeklyPlan.mockResolvedValue(WEEKLY_PLAN_RESPONSE);

    const { result } = renderHook(() => useWhoTargetsWithWeeklyPlan());

    await act(async () => {
      await result.current.saveAndGetWeeklyPlan(REQUEST);
    });

    await waitFor(() => {
      expect(result.current.targetsData).toEqual(TARGETS_RESPONSE);
      expect(result.current.weeklyPlanData).not.toBeNull();
    });

    expect(result.current.weeklyPlanData).toEqual({
      days: [
        {
          day: 1,
          dayName: 'Monday',
          kcal: 1800,
          total_cost: 18.5,
          coverage: { protein: 0.92, fiber: 0.8 },
          macros: { protein_g: 110, carbs_g: 180, fat_g: 60 },
          micros: { iron_mg: 12 },
          tips: ['Hydrate'],
          meals: [
            {
              title: 'Chicken bowl',
              title_translated: 'Chicken bowl',
              kcal: 620,
              price_est: 7.25,
              grams: { chicken: 180, rice: 150 },
              macros: { protein_g: 42, carbs_g: 58, fat_g: 14 },
              micros: { iron_mg: 3.4 },
            },
          ],
        },
      ],
      weekly_coverage: { protein: 0.95, fiber: 0.81 },
      shopping_list: { chicken: 1200, rice: 900 },
      metrics: {
        total_cost: 72.4,
        adherence_score: 0.88,
      },
      meta: {
        total_days: 1,
        has_incomplete_data: false,
      },
    });
  });

  it('passes the normalized VM into onSuccess', async () => {
    mockGetTargets.mockResolvedValue(TARGETS_RESPONSE);
    mockGetWeeklyPlan.mockResolvedValue(WEEKLY_PLAN_RESPONSE);

    const onSuccess = vi.fn();
    const { result } = renderHook(() =>
      useWhoTargetsWithWeeklyPlan({
        onSuccess,
      })
    );

    await act(async () => {
      await result.current.saveAndGetWeeklyPlan(REQUEST);
    });

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledTimes(1);
    });

    expect(onSuccess).toHaveBeenCalledWith(
      TARGETS_RESPONSE,
      expect.objectContaining({
        days: expect.any(Array),
        weekly_coverage: WEEKLY_PLAN_RESPONSE.weekly_coverage,
        shopping_list: WEEKLY_PLAN_RESPONSE.shopping_list,
        metrics: {
          total_cost: WEEKLY_PLAN_RESPONSE.total_cost,
          adherence_score: WEEKLY_PLAN_RESPONSE.adherence_score,
        },
      })
    );
  });
});

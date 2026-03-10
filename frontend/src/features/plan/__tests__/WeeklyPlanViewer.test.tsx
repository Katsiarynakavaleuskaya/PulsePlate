import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import WeeklyPlanViewer from '../WeeklyPlanViewer';
import type { WeekPlanVM } from '../../weekly-plan/model/types';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      if (key === 'plan.day_fallback' && options?.number) {
        return `Day ${options.number}`;
      }
      return key;
    },
  }),
}));

vi.mock('../../../lib/i18n', () => ({
  getClientLocale: vi.fn(() => 'en'),
}));

vi.mock('../../weekly-plan/hooks/useWeeklyPlan', () => ({
  useWeeklyPlan: vi.fn(),
}));

import { useWeeklyPlan } from '../../weekly-plan/hooks/useWeeklyPlan';

const mockUseWeeklyPlan = vi.mocked(useWeeklyPlan);

const WEEK_PLAN_VM: WeekPlanVM = {
  days: [
    {
      day: 1,
      dayName: 'Monday',
      kcal: 1800,
      total_cost: 18.4,
      coverage: { protein: 0.91 },
      macros: { protein_g: 120 },
      micros: { iron_mg: 12 },
      tips: ['Hydrate'],
      meals: [
        {
          title: 'Chicken bowl',
          title_translated: 'Chicken bowl',
          kcal: 620,
          price_est: 7.2,
          grams: { chicken: 180, rice: 150 },
          macros: { protein_g: 42, carbs_g: 58 },
          micros: { iron_mg: 3.4 },
        },
      ],
    },
  ],
  weekly_coverage: { protein: 0.95 },
  shopping_list: { chicken: 1200 },
  metrics: {
    total_cost: 72.4,
    adherence_score: 0.88,
  },
  meta: {
    total_days: 1,
    has_incomplete_data: false,
  },
};

describe('WeeklyPlanViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseWeeklyPlan.mockReturnValue({
      data: null,
      loading: false,
      error: null,
      refetch: vi.fn(),
      clearData: vi.fn(),
    });
  });

  it('renders loading state from the normalized weekly-plan hook', () => {
    mockUseWeeklyPlan.mockReturnValue({
      data: null,
      loading: true,
      error: null,
      refetch: vi.fn(),
      clearData: vi.fn(),
    });

    render(<WeeklyPlanViewer />);

    expect(screen.getByText('plan.loadingWeek')).toBeInTheDocument();
  });

  it('renders normalized week-plan view-model data', () => {
    mockUseWeeklyPlan.mockReturnValue({
      data: WEEK_PLAN_VM,
      loading: false,
      error: null,
      refetch: vi.fn(),
      clearData: vi.fn(),
    });

    render(<WeeklyPlanViewer />);

    expect(screen.getByText('Monday')).toBeInTheDocument();
    expect(screen.getByText('Chicken bowl')).toBeInTheDocument();
    expect(screen.getByText(/620 plan.kcal/)).toBeInTheDocument();
    expect(screen.getByText(/chicken: 180 g/i)).toBeInTheDocument();
    expect(screen.getByText(/rice: 150 g/i)).toBeInTheDocument();
  });
});

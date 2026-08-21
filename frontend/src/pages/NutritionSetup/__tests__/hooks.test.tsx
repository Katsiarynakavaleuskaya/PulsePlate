/** @vitest-environment jsdom */
import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getBmr, getPlate } from '../../../api/premium';
import { useSetupCalc } from '../hooks';
import type { SetupFormValues } from '../schema';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ i18n: { language: 'en' } }),
}));

vi.mock('../../../api/premium', () => ({
  getBmr: vi.fn(),
  getPlate: vi.fn(),
  getTargets: vi.fn(),
}));

const values: SetupFormValues = {
  sex: 'female',
  age: 34,
  height_cm: 168,
  weight_kg: 64,
  activity: 'moderate',
  goal: 'maintain',
  diet_flags: [],
};

const plateResponse = {
  kcal: 2154,
  macros: { protein_g: 132, carbs_g: 242, fat_g: 72, fiber_g: 31 },
  portions: {},
  layout: [],
  meals: [],
  meals_per_day: 3,
};

describe('useSetupCalc canonical BMR normalization', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getPlate).mockResolvedValue(plateResponse);
  });

  it('labels selected mifflin values correctly when formulas_used is reordered', async () => {
    vi.mocked(getBmr).mockResolvedValue({
      bmr: { mifflin: 1390.4, harris: 1420 },
      tdee: { mifflin: 2154.4, harris: 2201 },
      activity_level: 'Moderate activity',
      recommended_intake: {
        maintenance: 2154.4,
        weight_loss: 1723.52,
        weight_gain: 2585.28,
      },
      formulas_used: ['harris', 'mifflin'],
      notes: [],
    });

    const { result } = renderHook(() => useSetupCalc(values, 'en'));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeNull();
    expect(result.current.bmrData).toEqual({
      bmr: 1390,
      tdee: 2154,
      method: 'Mifflin-St Jeor',
    });
  });

  it('fails closed when canonical mifflin TDEE is absent instead of calculating it', async () => {
    vi.mocked(getBmr).mockResolvedValue({
      bmr: { mifflin: 1390, harris: 1420 },
      tdee: { harris: 2201 } as Record<string, number>,
      activity_level: 'Moderate activity',
      recommended_intake: {
        maintenance: 2154,
        weight_loss: 1723.2,
        weight_gain: 2584.8,
      },
      formulas_used: ['mifflin', 'harris'],
      notes: [],
    });

    const { result } = renderHook(() => useSetupCalc(values, 'en'));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.bmrData).toBeNull();
    expect(result.current.error).toContain('mifflin');
  });
});

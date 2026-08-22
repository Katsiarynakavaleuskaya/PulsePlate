/** @vitest-environment jsdom */
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getBmr, getPlate } from '../../../api/premium';
import type {
  BmrApiResponse,
  PlateResponse as ApiPlateResponse,
} from '../../../api/premium';
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

const plateResponse: ApiPlateResponse = {
  kcal: 2154,
  macros: { protein_g: 132, carbs_g: 242, fat_g: 72, fiber_g: 31 },
  portions: {},
  layout: [],
  meals: [],
  meals_per_day: 3,
};

const secondPlateResponse: ApiPlateResponse = {
  ...plateResponse,
  kcal: 2300,
  macros: { protein_g: 140, carbs_g: 260, fat_g: 75, fiber_g: 33 },
};

const bmrResponse = (bmr: number, tdee: number): BmrApiResponse => ({
  bmr: { mifflin: bmr, harris: bmr + 30 },
  tdee: { mifflin: tdee, harris: tdee + 45 },
  activity_level: 'Moderate activity',
  recommended_intake: {
    maintenance: tdee,
    weight_loss: tdee * 0.8,
    weight_gain: tdee * 1.2,
  },
  formulas_used: ['mifflin', 'harris'],
  notes: [],
});

function deferred<T>(): {
  promise: Promise<T>;
  resolve: (value: T | PromiseLike<T>) => void;
  reject: (reason?: unknown) => void;
} {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

describe('useSetupCalc canonical BMR normalization', () => {
  beforeEach(() => {
    vi.resetAllMocks();
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

  it('keeps request B loading when aborted request A rejects', async () => {
    const firstBmr = deferred<BmrApiResponse>();
    const secondBmr = deferred<BmrApiResponse>();
    const secondPlate = deferred<ApiPlateResponse>();
    vi.mocked(getBmr)
      .mockReturnValueOnce(firstBmr.promise)
      .mockReturnValueOnce(secondBmr.promise);
    vi.mocked(getPlate)
      .mockResolvedValueOnce(plateResponse)
      .mockReturnValueOnce(secondPlate.promise);
    const secondValues: SetupFormValues = { ...values, weight_kg: 65 };

    const { result, rerender } = renderHook(
      ({ profile }: { profile: SetupFormValues }) => useSetupCalc(profile, 'en'),
      { initialProps: { profile: values } },
    );
    await waitFor(() => expect(getBmr).toHaveBeenCalledTimes(1));
    const firstSignal = vi.mocked(getBmr).mock.calls[0]?.[1]?.signal;

    rerender({ profile: secondValues });
    await waitFor(() => expect(getBmr).toHaveBeenCalledTimes(2));
    expect(firstSignal?.aborted).toBe(true);
    expect(result.current.loading).toBe(true);

    await act(async () => {
      firstBmr.reject(new DOMException('aborted request A', 'AbortError'));
      await Promise.allSettled([firstBmr.promise]);
      await Promise.resolve();
    });

    expect(result.current.loading).toBe(true);
    expect(result.current.bmrData).toBeNull();
    expect(result.current.plateData).toBeNull();
    expect(result.current.error).toBeNull();

    await act(async () => {
      secondBmr.resolve(bmrResponse(1500, 2300));
      secondPlate.resolve(secondPlateResponse);
      await Promise.all([secondBmr.promise, secondPlate.promise]);
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeNull();
    expect(result.current.bmrData).toEqual({
      bmr: 1500,
      tdee: 2300,
      method: 'Mifflin-St Jeor',
    });
    expect(result.current.plateData?.plate.kcal).toBe(2300);
  });

  it('ignores request A success that arrives after request B owns the state', async () => {
    const firstBmr = deferred<BmrApiResponse>();
    const firstPlate = deferred<ApiPlateResponse>();
    const secondBmr = deferred<BmrApiResponse>();
    const secondPlate = deferred<ApiPlateResponse>();
    vi.mocked(getBmr)
      .mockReturnValueOnce(firstBmr.promise)
      .mockReturnValueOnce(secondBmr.promise);
    vi.mocked(getPlate)
      .mockReturnValueOnce(firstPlate.promise)
      .mockReturnValueOnce(secondPlate.promise);
    const secondValues: SetupFormValues = { ...values, weight_kg: 66 };

    const { result, rerender } = renderHook(
      ({ profile }: { profile: SetupFormValues }) => useSetupCalc(profile, 'en'),
      { initialProps: { profile: values } },
    );
    await waitFor(() => expect(getBmr).toHaveBeenCalledTimes(1));
    const firstSignal = vi.mocked(getBmr).mock.calls[0]?.[1]?.signal;

    rerender({ profile: secondValues });
    await waitFor(() => expect(getBmr).toHaveBeenCalledTimes(2));
    expect(firstSignal?.aborted).toBe(true);

    await act(async () => {
      secondBmr.resolve(bmrResponse(1500, 2300));
      secondPlate.resolve(secondPlateResponse);
      await Promise.all([secondBmr.promise, secondPlate.promise]);
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.bmrData?.bmr).toBe(1500);
    expect(result.current.plateData?.plate.kcal).toBe(2300);

    await act(async () => {
      firstBmr.resolve(bmrResponse(1390, 2154));
      firstPlate.resolve(plateResponse);
      await Promise.all([firstBmr.promise, firstPlate.promise]);
      await Promise.resolve();
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.bmrData?.bmr).toBe(1500);
    expect(result.current.bmrData?.tdee).toBe(2300);
    expect(result.current.plateData?.plate.kcal).toBe(2300);
  });
});

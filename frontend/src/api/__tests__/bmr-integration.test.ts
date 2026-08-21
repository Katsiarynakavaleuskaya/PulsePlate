import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getBmr } from '../premium/bmr';
import type { BmrApiResponse, BmrRequest } from '../premium/bmr';

vi.mock('../client', async () => {
  const actual = await vi.importActual<typeof import('../client')>('../client');
  return {
    ...actual,
    api: vi.fn(),
  };
});

import { api } from '../client';

describe('canonical PRO BMR integration', () => {
  const mockApi = vi.mocked(api);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it('posts the generated BMR contract to the canonical route', async () => {
    const request: BmrRequest = {
      sex: 'female',
      age: 34,
      height_cm: 168,
      weight_kg: 64,
      activity: 'moderate',
      lang: 'en',
    };
    const response: BmrApiResponse = {
      bmr: { mifflin: 1390, harris: 1420 },
      tdee: { mifflin: 2154, harris: 2201 },
      activity_level: 'Moderate activity',
      recommended_intake: {
        maintenance: 2154,
        weight_loss: 1723.2,
        weight_gain: 2584.8,
      },
      formulas_used: ['mifflin', 'harris'],
      notes: [],
    };
    mockApi.mockResolvedValue(response);

    await expect(getBmr(request)).resolves.toEqual(response);
    expect(mockApi).toHaveBeenCalledWith(
      '/api/v1/pro/nutrition/bmr',
      expect.objectContaining({ method: 'POST', body: request, signal: undefined }),
      undefined,
      true,
    );
  });
});

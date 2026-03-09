import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getWeeklyPlan } from '../premium/weekly-plan';
import type { WeeklyMenuResponse, WeekPlanRequest } from '../premium/weekly-plan';

vi.mock('../client', () => ({
  api: vi.fn(),
}));

import { api } from '../client';

function createMockWeeklyPlanResponse(
  overrides: Partial<WeeklyMenuResponse> = {}
): WeeklyMenuResponse {
  return {
    daily_menus: [
      {
        coverage: { protein: 96, calcium: 88 },
        kcal: 1850,
        macros: { protein_g: 110, carbs_g: 180, fat_g: 65 },
        meals: [
          {
            title: 'Chicken bowl',
            title_translated: 'Chicken bowl',
            grams: { chicken: 180, rice: 150 },
            kcal: 620,
            macros: { protein_g: 42, carbs_g: 58, fat_g: 14 },
            micros: { iron_mg: 3.4 },
            price_est: 7.25,
          },
        ],
        micros: { iron_mg: 10.5, vitamin_c_mg: 88 },
        tips: ['Hydrate well'],
        total_cost: 18.4,
      },
    ],
    weekly_coverage: {
      protein: 97,
      iron: 93,
      vitamin_c: 105,
      calcium: 89,
    },
    shopping_list: {
      chicken: 1260,
      rice: 1050,
    },
    total_cost: 74.6,
    adherence_score: 0.87,
    ...overrides,
  };
}

describe('Weekly Plan API Integration', () => {
  const mockApi = vi.mocked(api);

  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv('VITE_API_BASE', 'http://test-api.com');
  });

  afterEach(() => {
    vi.resetAllMocks();
    vi.unstubAllEnvs();
  });

  describe('Successful API calls (200)', () => {
    it('should generate weekly plan successfully with valid profile request', async () => {
      const mockRequest: WeekPlanRequest = {
        sex: 'female',
        age: 25,
        height_cm: 165,
        weight_kg: 60,
        activity: 'moderate',
        goal: 'maintain',
        diet_flags: [],
        lang: 'en',
      };
      const mockResponse = createMockWeeklyPlanResponse();

      mockApi.mockResolvedValue(mockResponse);

      const result = await getWeeklyPlan(mockRequest);

      expect(mockApi).toHaveBeenCalledWith(
        '/api/v1/pro/meal/weekly',
        expect.objectContaining({
          method: 'POST',
          body: mockRequest,
          signal: undefined,
        }),
        undefined,
        true
      );
      expect(result).toEqual(mockResponse);
    });

    it('should accept canonical request with ready targets payload', async () => {
      const mockRequest: WeekPlanRequest = {
        targets: {
          kcal: 2100,
          macros: { protein_g: 140, carbs_g: 220, fat_g: 70 },
          micro: { iron_mg: 18, calcium_mg: 1000 },
          water_ml: 2200,
          activity_week: { moderate_aerobic_min: 150, strength_sessions: 2 },
        },
        diet_flags: ['HIGH_PROTEIN', 'LOW_CARB'],
        lang: 'ru',
        activity: 'active',
        goal: 'loss',
      };
      const mockResponse = createMockWeeklyPlanResponse({
        daily_menus: [],
        total_cost: 0,
      });

      mockApi.mockResolvedValue(mockResponse);

      const result = await getWeeklyPlan(mockRequest);

      expect(result).toEqual(mockResponse);
    });
  });

  describe('Error handling', () => {
    it('should handle authentication errors', async () => {
      const mockRequest: WeekPlanRequest = {
        sex: 'female',
        age: 25,
        height_cm: 165,
        weight_kg: 60,
        activity: 'moderate',
        goal: 'maintain',
        lang: 'en',
      };

      const authError = new Error('Unauthorized');
      authError.name = 'AuthError';
      mockApi.mockRejectedValue(authError);

      await expect(getWeeklyPlan(mockRequest)).rejects.toThrow('Unauthorized');
    });

    it('should handle missing required fields', async () => {
      const invalidRequest = {
        activity: 'moderate',
        goal: 'maintain',
        lang: 'en',
      } as WeekPlanRequest;

      const validationError = new Error('Validation error: missing required fields');
      validationError.name = 'ValidationError';
      mockApi.mockRejectedValue(validationError);

      await expect(getWeeklyPlan(invalidRequest)).rejects.toThrow(
        'Validation error: missing required fields'
      );
    });

    it('should handle network timeout', async () => {
      const mockRequest: WeekPlanRequest = {
        sex: 'female',
        age: 25,
        height_cm: 165,
        weight_kg: 60,
        activity: 'moderate',
        goal: 'maintain',
        lang: 'en',
      };

      const timeoutError = new Error('Request timeout');
      timeoutError.name = 'TimeoutError';
      mockApi.mockRejectedValue(timeoutError);

      await expect(getWeeklyPlan(mockRequest)).rejects.toThrow('Request timeout');
    });
  });

  describe('Request options', () => {
    it('should pass through request options correctly', async () => {
      const mockRequest: WeekPlanRequest = {
        sex: 'female',
        age: 25,
        height_cm: 165,
        weight_kg: 60,
        activity: 'moderate',
        goal: 'maintain',
        lang: 'en',
      };
      const mockResponse = createMockWeeklyPlanResponse({ daily_menus: [] });

      mockApi.mockResolvedValue(mockResponse);

      const options = {
        signal: new AbortController().signal,
        onAuthError: vi.fn(),
      };

      await getWeeklyPlan(mockRequest, options);

      expect(mockApi).toHaveBeenCalledWith(
        '/api/v1/pro/meal/weekly',
        expect.objectContaining({
          method: 'POST',
          body: mockRequest,
          signal: options.signal,
        }),
        { onAuthError: options.onAuthError },
        true
      );
    });
  });
});

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getWeeklyPlan } from '../premium/weekly-plan';
import type { WeeklyMenuResponse, WeekPlanRequest } from '../premium/weekly-plan';

// Mock the API client
vi.mock('../client', () => ({
  api: vi.fn(),
}));

import { api } from '../client';

describe('Weekly Plan API Integration', () => {
  const mockApi = vi.mocked(api);

  beforeEach(() => {
    vi.clearAllMocks();
    // Set up environment for CI
    vi.stubEnv('VITE_API_BASE', 'http://test-api.com');
  });

  afterEach(() => {
    vi.resetAllMocks();
    vi.unstubAllEnvs();
  });

  describe('Successful API calls (200)', () => {
    it('should generate weekly plan successfully with valid request', async () => {
      const mockRequest: WeekPlanRequest = {
        sex: 'female',
        age: 25,
        height_cm: 165,
        weight_kg: 60,
        activity: 'moderate',
        goal: 'maintain',
        life_stage: 'adult',
        lang: 'en',
      };

      const mockResponse = {
        week_summary: {
          total_calories: 14000,
          total_protein: 1050,
          total_carbs: 1750,
          total_fat: 469,
        },
        daily_menus: [
          {
            day: 'Monday',
            meals: [
              {
                name: 'Breakfast',
                calories: 500,
                protein: 25,
                carbs: 60,
                fat: 15,
              },
              {
                name: 'Lunch',
                calories: 600,
                protein: 35,
                carbs: 70,
                fat: 20,
              },
              {
                name: 'Dinner',
                calories: 500,
                protein: 30,
                carbs: 50,
                fat: 18,
              },
            ],
          },
          // ... other days
        ],
        weekly_coverage: {
          protein: 95,
          carbs: 98,
          fat: 92,
          fiber: 85,
        },
        shopping_list: {
          'chicken breast': 500,
          'brown rice': 1000,
          'broccoli': 300,
          'olive oil': 200,
        },
        total_cost: 45.50,
        adherence_score: 87,
      } as unknown as WeeklyMenuResponse;

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

    it('should handle request with all optional fields', async () => {
      const mockRequest: WeekPlanRequest = {
        sex: 'male',
        age: 30,
        height_cm: 180,
        weight_kg: 80,
        activity: 'very_active',
        goal: 'loss',
        deficit_pct: 20,
        surplus_pct: null,
        bodyfat: 15,
        diet_flags: ['HIGH_PROTEIN', 'LOW_CARB'],
        life_stage: 'adult',
        lang: 'ru',
      };

      const mockResponse = {
        week_summary: {
          total_calories: 16800,
          total_protein: 1400,
          total_carbs: 1050,
          total_fat: 560,
        },
        daily_menus: [],
        weekly_coverage: {
          protein: 98,
          carbs: 85,
          fat: 95,
          fiber: 80,
        },
        shopping_list: {
          'salmon': 600,
          'quinoa': 800,
          'spinach': 400,
          'avocado': 300,
        },
        total_cost: 65.75,
        adherence_score: 92,
      } as unknown as WeeklyMenuResponse;

      mockApi.mockResolvedValue(mockResponse);

      const result = await getWeeklyPlan(mockRequest);

      expect(result).toEqual(mockResponse);
    });

    it('should handle different life stages', async () => {
      const lifeStages = ['child', 'teen', 'adult', 'pregnant', 'lactating', 'elderly'] as const;

      for (const lifeStage of lifeStages) {
        const mockRequest: WeekPlanRequest = {
          sex: 'female',
          age: lifeStage === 'child' ? 8 : lifeStage === 'teen' ? 16 : 25,
          height_cm: 165,
          weight_kg: 60,
          activity: 'moderate',
          goal: 'maintain',
          life_stage: lifeStage,
          lang: 'en',
        };

        const mockResponse = {
          week_summary: {
            total_calories: 14000,
            total_protein: 1050,
            total_carbs: 1750,
            total_fat: 469,
          },
          daily_menus: [],
          weekly_coverage: {
            protein: 95,
            carbs: 98,
            fat: 92,
            fiber: 85,
          },
          shopping_list: {
            'chicken breast': 500,
            'brown rice': 1000,
            'broccoli': 300,
          },
          total_cost: 45.50,
          adherence_score: 87,
        } as unknown as WeeklyMenuResponse;

        mockApi.mockResolvedValue(mockResponse);

        const result = await getWeeklyPlan(mockRequest);

        expect(result).toEqual(mockResponse);
      }
    });
  });

  describe('Error handling (401)', () => {
    it('should handle authentication errors', async () => {
      const mockRequest: WeekPlanRequest = {
        sex: 'female',
        age: 25,
        height_cm: 165,
        weight_kg: 60,
        activity: 'moderate',
        goal: 'maintain',
        life_stage: 'adult',
        lang: 'en',
      };

      const authError = new Error('Unauthorized');
      authError.name = 'AuthError';
      mockApi.mockRejectedValue(authError);

      await expect(getWeeklyPlan(mockRequest)).rejects.toThrow('Unauthorized');
    });

    it('should handle missing API key', async () => {
      const mockRequest: WeekPlanRequest = {
        sex: 'female',
        age: 25,
        height_cm: 165,
        weight_kg: 60,
        activity: 'moderate',
        goal: 'maintain',
        life_stage: 'adult',
        lang: 'en',
      };

      const keyError = new Error('API key required');
      keyError.name = 'MissingApiKey';
      mockApi.mockRejectedValue(keyError);

      await expect(getWeeklyPlan(mockRequest)).rejects.toThrow('API key required');
    });
  });

  describe('Validation errors (422)', () => {
    it('should handle invalid request data', async () => {
      const invalidRequest = {
        sex: 'female',
        age: -5, // Invalid age
        height_cm: 165,
        weight_kg: 60,
        activity: 'moderate',
        goal: 'maintain',
        life_stage: 'adult',
        lang: 'en',
      } as WeekPlanRequest;

      const validationError = new Error('Validation error: age must be positive');
      validationError.name = 'ValidationError';
      mockApi.mockRejectedValue(validationError);

      await expect(getWeeklyPlan(invalidRequest)).rejects.toThrow('Validation error: age must be positive');
    });

    it('should handle missing required fields', async () => {
      const invalidRequest = {
        sex: 'female',
        // Missing age, height, weight, etc.
        activity: 'moderate',
        goal: 'maintain',
        life_stage: 'adult',
        lang: 'en',
      } as any;

      const validationError = new Error('Validation error: missing required fields');
      validationError.name = 'ValidationError';
      mockApi.mockRejectedValue(validationError);

      await expect(getWeeklyPlan(invalidRequest)).rejects.toThrow('Validation error: missing required fields');
    });
  });

  describe('Network errors', () => {
    it('should handle network timeout', async () => {
      const mockRequest: WeekPlanRequest = {
        sex: 'female',
        age: 25,
        height_cm: 165,
        weight_kg: 60,
        activity: 'moderate',
        goal: 'maintain',
        life_stage: 'adult',
        lang: 'en',
      };

      const timeoutError = new Error('Request timeout');
      timeoutError.name = 'TimeoutError';
      mockApi.mockRejectedValue(timeoutError);

      await expect(getWeeklyPlan(mockRequest)).rejects.toThrow('Request timeout');
    });

    it('should handle server errors (500)', async () => {
      const mockRequest: WeekPlanRequest = {
        sex: 'female',
        age: 25,
        height_cm: 165,
        weight_kg: 60,
        activity: 'moderate',
        goal: 'maintain',
        life_stage: 'adult',
        lang: 'en',
      };

      const serverError = new Error('Internal server error');
      serverError.name = 'ServerError';
      mockApi.mockRejectedValue(serverError);

      await expect(getWeeklyPlan(mockRequest)).rejects.toThrow('Internal server error');
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
        life_stage: 'adult',
        lang: 'en',
      };

      const mockResponse = {
        week_summary: {},
        daily_menus: [],
        weekly_coverage: {},
        shopping_list: {},
        total_cost: 0,
        adherence_score: 0,
      } as unknown as WeeklyMenuResponse;

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

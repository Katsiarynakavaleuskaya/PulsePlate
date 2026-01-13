import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getTargets } from '../premium/targets';
import type { TargetsRequest, TargetsApiResponse } from '../premium/types';

// Mock the API client
vi.mock('../client', () => ({
  api: vi.fn(),
}));

import { api } from '../client';

describe('WHO Targets API Integration', () => {
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
    it('should fetch targets successfully with valid request', async () => {
      const mockRequest: TargetsRequest = {
        sex: 'female',
        age: 25,
        height_cm: 165,
        weight_kg: 60,
        activity: 'moderate',
        goal: 'maintain',
        life_stage: 'adult',
        lang: 'en',
      };

      const mockResponse: TargetsApiResponse = {
        kcal_daily: 2000,
        macros: {
          protein_g: 150,
          carbs_g: 250,
          fat_g: 67,
          fiber_g: 25,
        },
        water_ml: 2000,
        priority_micros: {
          iron: 18,
          calcium: 1000,
        },
        activity_weekly: {
          moderate_aerobic_min: 150,
          strength_sessions: 2,
          steps_daily: 8000,
        },
        calculation_date: '2024-01-15T10:30:00Z',
        warnings: [
          {
            type: 'iron',
            message: 'Consider increasing iron-rich foods',
            severity: 'warning',
          },
        ],
      };

      mockApi.mockResolvedValue(mockResponse);

      const result = await getTargets(mockRequest);

      expect(mockApi).toHaveBeenCalledWith(
        '/api/v1/pro/nutrition/targets',
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
      const mockRequest: TargetsRequest = {
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

      const mockResponse: TargetsApiResponse = {
        kcal_daily: 2400,
        macros: {
          protein_g: 200,
          carbs_g: 150,
          fat_g: 80,
          fiber_g: 30,
        },
        water_ml: 2500,
        priority_micros: {
          iron: 20,
          calcium: 1200,
        },
        activity_weekly: {
          moderate_aerobic_min: 200,
          strength_sessions: 3,
          steps_daily: 10000,
        },
        calculation_date: '2024-01-15T10:30:00Z',
        warnings: [],
      };

      mockApi.mockResolvedValue(mockResponse);

      const result = await getTargets(mockRequest);

      expect(result).toEqual(mockResponse);
    });

    it('should handle different life stages', async () => {
      const lifeStages = ['child', 'teen', 'adult', 'pregnant', 'lactating', 'elderly'] as const;

      for (const lifeStage of lifeStages) {
        const mockRequest: TargetsRequest = {
          sex: 'female',
          age: lifeStage === 'child' ? 8 : lifeStage === 'teen' ? 16 : 25,
          height_cm: 165,
          weight_kg: 60,
          activity: 'moderate',
          goal: 'maintain',
          life_stage: lifeStage,
          lang: 'en',
        };

        const mockResponse: TargetsApiResponse = {
          kcal_daily: 2000,
          macros: {
            protein_g: 150,
            carbs_g: 250,
            fat_g: 67,
            fiber_g: 25,
          },
          water_ml: 2000,
          priority_micros: {
            iron: 18,
            calcium: 1000,
          },
          activity_weekly: {
            moderate_aerobic_min: 150,
            strength_sessions: 2,
            steps_daily: 8000,
          },
          calculation_date: '2024-01-15T10:30:00Z',
          warnings: [],
        };

        mockApi.mockResolvedValue(mockResponse);

        const result = await getTargets(mockRequest);

        expect(result).toEqual(mockResponse);
      }
    });
  });

  describe('Error handling (401)', () => {
    it('should handle authentication errors', async () => {
      const mockRequest: TargetsRequest = {
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

      await expect(getTargets(mockRequest)).rejects.toThrow('Unauthorized');
    });

    it('should handle missing API key', async () => {
      const mockRequest: TargetsRequest = {
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

      await expect(getTargets(mockRequest)).rejects.toThrow('API key required');
    });
  });

  describe('Validation errors (422)', () => {
    it('should handle invalid age', async () => {
      const invalidRequest = {
        sex: 'female',
        age: -5, // Invalid age
        height_cm: 165,
        weight_kg: 60,
        activity: 'moderate',
        goal: 'maintain',
        life_stage: 'adult',
        lang: 'en',
      } as TargetsRequest;

      const validationError = new Error('Validation error: age must be positive');
      validationError.name = 'ValidationError';
      mockApi.mockRejectedValue(validationError);

      await expect(getTargets(invalidRequest)).rejects.toThrow('Validation error: age must be positive');
    });

    it('should handle invalid height/weight', async () => {
      const invalidRequest = {
        sex: 'female',
        age: 25,
        height_cm: 0, // Invalid height
        weight_kg: -10, // Invalid weight
        activity: 'moderate',
        goal: 'maintain',
        life_stage: 'adult',
        lang: 'en',
      } as TargetsRequest;

      const validationError = new Error('Validation error: height and weight must be positive');
      validationError.name = 'ValidationError';
      mockApi.mockRejectedValue(validationError);

      await expect(getTargets(invalidRequest)).rejects.toThrow('Validation error: height and weight must be positive');
    });

    it('should handle invalid activity level', async () => {
      const invalidRequest = {
        sex: 'female' as const,
        age: 25,
        height_cm: 165,
        weight_kg: 60,
        activity: 'invalid_activity' as any,
        goal: 'maintain' as const,
        life_stage: 'adult' as const,
        lang: 'en',
      };

      const validationError = new Error('Validation error: invalid activity level');
      validationError.name = 'ValidationError';
      mockApi.mockRejectedValue(validationError);

      await expect(getTargets(invalidRequest)).rejects.toThrow('Validation error: invalid activity level');
    });

    it('should handle invalid goal with deficit/surplus', async () => {
      const invalidRequest = {
        sex: 'female' as const,
        age: 25,
        height_cm: 165,
        weight_kg: 60,
        activity: 'moderate' as const,
        goal: 'maintain' as const,
        deficit_pct: 20, // Invalid: deficit should not be set for maintain goal
        surplus_pct: 10, // Invalid: surplus should not be set for maintain goal
        life_stage: 'adult' as const,
        lang: 'en',
      };

      const validationError = new Error('Validation error: deficit/surplus not allowed for maintain goal');
      validationError.name = 'ValidationError';
      mockApi.mockRejectedValue(validationError);

      await expect(getTargets(invalidRequest)).rejects.toThrow('Validation error: deficit/surplus not allowed for maintain goal');
    });
  });

  describe('Network errors', () => {
    it('should handle network timeout', async () => {
      const mockRequest: TargetsRequest = {
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

      await expect(getTargets(mockRequest)).rejects.toThrow('Request timeout');
    });

    it('should handle network connectivity issues', async () => {
      const mockRequest: TargetsRequest = {
        sex: 'female',
        age: 25,
        height_cm: 165,
        weight_kg: 60,
        activity: 'moderate',
        goal: 'maintain',
        life_stage: 'adult',
        lang: 'en',
      };

      const networkError = new Error('Network error');
      networkError.name = 'NetworkError';
      mockApi.mockRejectedValue(networkError);

      await expect(getTargets(mockRequest)).rejects.toThrow('Network error');
    });

    it('should handle server errors (500)', async () => {
      const mockRequest: TargetsRequest = {
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

      await expect(getTargets(mockRequest)).rejects.toThrow('Internal server error');
    });
  });

  describe('Request options', () => {
    it('should pass through request options correctly', async () => {
      const mockRequest: TargetsRequest = {
        sex: 'female',
        age: 25,
        height_cm: 165,
        weight_kg: 60,
        activity: 'moderate',
        goal: 'maintain',
        life_stage: 'adult',
        lang: 'en',
      };

      const mockResponse: TargetsApiResponse = {
        kcal_daily: 2000,
        macros: {
          protein_g: 150,
          carbs_g: 250,
          fat_g: 67,
          fiber_g: 25,
        },
        water_ml: 2000,
        priority_micros: {
          iron: 18,
          calcium: 1000,
        },
        activity_weekly: {
          moderate_aerobic_min: 150,
          strength_sessions: 2,
          steps_daily: 8000,
        },
        calculation_date: '2024-01-15T10:30:00Z',
        warnings: [],
      };

      mockApi.mockResolvedValue(mockResponse);

      const options = {
        signal: new AbortController().signal,
        onAuthError: vi.fn(),
      };

      await getTargets(mockRequest, options);

      expect(mockApi).toHaveBeenCalledWith(
        '/api/v1/pro/nutrition/targets',
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

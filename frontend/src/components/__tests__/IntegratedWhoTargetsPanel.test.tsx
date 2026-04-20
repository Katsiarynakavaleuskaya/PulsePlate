import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { IntegratedWhoTargetsPanel } from '../WhoTargetsPanel/IntegratedWhoTargetsPanel';
import type { TargetsRequest } from '../../api/premium/types';
import type { WeekPlanVM } from '../../features/weekly-plan/model/types';

// Mock the hook
vi.mock('../../hooks/useWhoTargetsWithWeeklyPlan', () => ({
  useWhoTargetsWithWeeklyPlan: vi.fn(),
}));

import { useWhoTargetsWithWeeklyPlan } from '../../hooks/useWhoTargetsWithWeeklyPlan';

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => fallback || key,
    i18n: { language: 'en' },
  }),
}));

describe('IntegratedWhoTargetsPanel', () => {
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

  const mockTargetsData = {
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

  const mockWeeklyPlanData: WeekPlanVM = {
    days: [],
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
    metrics: {
      total_cost: 45.5,
      adherence_score: 87,
    },
    meta: {
      total_days: 0,
      has_incomplete_data: false,
    },
  };

  const mockHook = vi.mocked(useWhoTargetsWithWeeklyPlan);

  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementation
    mockHook.mockReturnValue({
      targetsData: null,
      targetsLoading: false,
      targetsError: null,
      weeklyPlanData: null,
      weeklyPlanLoading: false,
      weeklyPlanError: null,
      fetchTargets: vi.fn(),
      saveAndGetWeeklyPlan: vi.fn(),
      retry: vi.fn(),
      clearData: vi.fn(),
    });
  });

  describe('Loading states', () => {
    it('should show loading state when targets are loading', () => {
      mockHook.mockReturnValue({
        targetsData: null,
        targetsLoading: true,
        targetsError: null,
        weeklyPlanData: null,
        weeklyPlanLoading: false,
        weeklyPlanError: null,
        fetchTargets: vi.fn(),
        saveAndGetWeeklyPlan: vi.fn(),
        retry: vi.fn(),
        clearData: vi.fn(),
      });

      render(<IntegratedWhoTargetsPanel request={mockRequest} />);

      expect(screen.getByTestId('who-targets-panel')).toHaveClass('who-targets-panel--loading');
      expect(screen.getByText('WHO Nutrition Targets')).toBeInTheDocument();
    });

    it('should show loading state when weekly plan is loading', () => {
      mockHook.mockReturnValue({
        targetsData: mockTargetsData,
        targetsLoading: false,
        targetsError: null,
        weeklyPlanData: null,
        weeklyPlanLoading: true,
        weeklyPlanError: null,
        fetchTargets: vi.fn(),
        saveAndGetWeeklyPlan: vi.fn(),
        retry: vi.fn(),
        clearData: vi.fn(),
      });

      render(<IntegratedWhoTargetsPanel request={mockRequest} />);

      expect(screen.getByTestId('who-targets-panel')).toHaveClass('who-targets-panel--loading');
    });
  });

  describe('Error states', () => {
    it('should show error state when targets fetch fails', () => {
      mockHook.mockReturnValue({
        targetsData: null,
        targetsLoading: false,
        targetsError: 'Failed to fetch targets',
        weeklyPlanData: null,
        weeklyPlanLoading: false,
        weeklyPlanError: null,
        fetchTargets: vi.fn(),
        saveAndGetWeeklyPlan: vi.fn(),
        retry: vi.fn(),
        clearData: vi.fn(),
      });

      render(<IntegratedWhoTargetsPanel request={mockRequest} />);

      expect(screen.getByTestId('who-targets-panel')).toHaveClass('who-targets-panel--error');
      expect(screen.getByText('Failed to fetch targets')).toBeInTheDocument();
    });

    it('should show error state when weekly plan generation fails', () => {
      mockHook.mockReturnValue({
        targetsData: mockTargetsData,
        targetsLoading: false,
        targetsError: null,
        weeklyPlanData: null,
        weeklyPlanLoading: false,
        weeklyPlanError: 'Failed to generate weekly plan',
        fetchTargets: vi.fn(),
        saveAndGetWeeklyPlan: vi.fn(),
        retry: vi.fn(),
        clearData: vi.fn(),
      });

      render(<IntegratedWhoTargetsPanel request={mockRequest} />);

      expect(screen.getByTestId('who-targets-panel')).toHaveClass('who-targets-panel--error');
      expect(screen.getByText('Failed to generate weekly plan')).toBeInTheDocument();
    });
  });

  describe('Success states', () => {
    it('should show targets data when loaded successfully', () => {
      mockHook.mockReturnValue({
        targetsData: mockTargetsData,
        targetsLoading: false,
        targetsError: null,
        weeklyPlanData: null,
        weeklyPlanLoading: false,
        weeklyPlanError: null,
        fetchTargets: vi.fn(),
        saveAndGetWeeklyPlan: vi.fn(),
        retry: vi.fn(),
        clearData: vi.fn(),
      });

      render(<IntegratedWhoTargetsPanel request={mockRequest} />);

      expect(screen.getByTestId('who-targets-panel')).toHaveClass('who-targets-panel--loaded');
      expect(screen.getAllByText('2,000')).toHaveLength(2); // kcal_daily and water_ml
      expect(screen.getByText('Save & Get Weekly Plan')).toBeInTheDocument();
    });

    it('should show empty state when no request is provided', () => {
      mockHook.mockReturnValue({
        targetsData: null,
        targetsLoading: false,
        targetsError: null,
        weeklyPlanData: null,
        weeklyPlanLoading: false,
        weeklyPlanError: null,
        fetchTargets: vi.fn(),
        saveAndGetWeeklyPlan: vi.fn(),
        retry: vi.fn(),
        clearData: vi.fn(),
      });

      render(<IntegratedWhoTargetsPanel request={null} />);

      expect(screen.getByTestId('who-targets-panel')).toHaveClass('who-targets-panel--empty');
    });
  });

  describe('CTA button integration', () => {
    it('should call saveAndGetWeeklyPlan when CTA button is clicked', async () => {
      const user = userEvent.setup();
      const mockSaveAndGetWeeklyPlan = vi.fn().mockResolvedValue(undefined);

      mockHook.mockReturnValue({
        targetsData: mockTargetsData,
        targetsLoading: false,
        targetsError: null,
        weeklyPlanData: null,
        weeklyPlanLoading: false,
        weeklyPlanError: null,
        fetchTargets: vi.fn(),
        saveAndGetWeeklyPlan: mockSaveAndGetWeeklyPlan,
        retry: vi.fn(),
        clearData: vi.fn(),
      });

      render(<IntegratedWhoTargetsPanel request={mockRequest} />);

      const ctaButton = screen.getByRole('button', { name: /save & get weekly plan/i });
      await user.click(ctaButton);

      expect(mockSaveAndGetWeeklyPlan).toHaveBeenCalledWith(mockRequest);
    });

    it('should handle keyboard activation of CTA button', async () => {
      const user = userEvent.setup();
      const mockSaveAndGetWeeklyPlan = vi.fn().mockResolvedValue(undefined);

      mockHook.mockReturnValue({
        targetsData: mockTargetsData,
        targetsLoading: false,
        targetsError: null,
        weeklyPlanData: null,
        weeklyPlanLoading: false,
        weeklyPlanError: null,
        fetchTargets: vi.fn(),
        saveAndGetWeeklyPlan: mockSaveAndGetWeeklyPlan,
        retry: vi.fn(),
        clearData: vi.fn(),
      });

      render(<IntegratedWhoTargetsPanel request={mockRequest} />);

      const ctaButton = screen.getByRole('button', { name: /save & get weekly plan/i });
      ctaButton.focus();
      await user.keyboard('{Enter}');

      expect(mockSaveAndGetWeeklyPlan).toHaveBeenCalledWith(mockRequest);
    });
  });

  describe('Retry functionality', () => {
    it('should call retry when retry button is clicked', async () => {
      const user = userEvent.setup();
      const mockRetry = vi.fn();

      mockHook.mockReturnValue({
        targetsData: null,
        targetsLoading: false,
        targetsError: 'Failed to fetch targets',
        weeklyPlanData: null,
        weeklyPlanLoading: false,
        weeklyPlanError: null,
        fetchTargets: vi.fn(),
        saveAndGetWeeklyPlan: vi.fn(),
        retry: mockRetry,
        clearData: vi.fn(),
      });

      render(<IntegratedWhoTargetsPanel request={mockRequest} />);

      const retryButton = screen.getByRole('button', { name: /try again/i });
      await user.click(retryButton);

      expect(mockRetry).toHaveBeenCalled();
    });
  });

  describe('Callbacks', () => {
    it('should call onWeeklyPlanGenerated when weekly plan is generated', () => {
      const mockOnWeeklyPlanGenerated = vi.fn();
      const mockOnError = vi.fn();
      let capturedOnSuccess: ((targets: typeof mockTargetsData, weeklyPlan: WeekPlanVM) => void) | undefined;

      mockHook.mockImplementation((options = {}) => {
        capturedOnSuccess = options.onSuccess as typeof capturedOnSuccess;
        return {
          targetsData: mockTargetsData,
          targetsLoading: false,
          targetsError: null,
          weeklyPlanData: mockWeeklyPlanData,
          weeklyPlanLoading: false,
          weeklyPlanError: null,
          fetchTargets: vi.fn(),
          saveAndGetWeeklyPlan: vi.fn(),
          retry: vi.fn(),
          clearData: vi.fn(),
        };
      });

      render(
        <IntegratedWhoTargetsPanel
          request={mockRequest}
          onWeeklyPlanGenerated={mockOnWeeklyPlanGenerated}
          onError={mockOnError}
        />
      );

      expect(screen.getByTestId('who-targets-panel')).toHaveClass('who-targets-panel--loaded');
      expect(capturedOnSuccess).toBeTypeOf('function');
      capturedOnSuccess?.(mockTargetsData, mockWeeklyPlanData);
      expect(mockOnWeeklyPlanGenerated).toHaveBeenCalledWith(mockWeeklyPlanData);
      expect(mockOnError).not.toHaveBeenCalled();
    });

    it('should pass onError through the hook options', () => {
      const mockOnError = vi.fn();
      let capturedOnError: ((error: Error) => void) | undefined;

      mockHook.mockImplementation((options = {}) => {
        capturedOnError = options.onError as typeof capturedOnError;
        return {
          targetsData: mockTargetsData,
          targetsLoading: false,
          targetsError: null,
          weeklyPlanData: null,
          weeklyPlanLoading: false,
          weeklyPlanError: null,
          fetchTargets: vi.fn(),
          saveAndGetWeeklyPlan: vi.fn(),
          retry: vi.fn(),
          clearData: vi.fn(),
        };
      });

      render(<IntegratedWhoTargetsPanel request={mockRequest} onError={mockOnError} />);

      const error = new Error('weekly-plan-failed');
      expect(capturedOnError).toBeTypeOf('function');
      capturedOnError?.(error);
      expect(mockOnError).toHaveBeenCalledWith(error);
    });
  });

  describe('Error handling', () => {
    it('should handle missing request gracefully', async () => {
      const mockSaveAndGetWeeklyPlan = vi.fn();

      mockHook.mockReturnValue({
        targetsData: mockTargetsData,
        targetsLoading: false,
        targetsError: null,
        weeklyPlanData: null,
        weeklyPlanLoading: false,
        weeklyPlanError: null,
        fetchTargets: vi.fn(),
        saveAndGetWeeklyPlan: mockSaveAndGetWeeklyPlan,
        retry: vi.fn(),
        clearData: vi.fn(),
      });

      render(<IntegratedWhoTargetsPanel request={null} />);

      // Should not show CTA button when no request is available
      expect(screen.queryByRole('button', { name: /save & get weekly plan/i })).not.toBeInTheDocument();
    });
  });
});

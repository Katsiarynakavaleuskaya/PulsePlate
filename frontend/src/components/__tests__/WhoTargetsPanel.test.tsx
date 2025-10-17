import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { WhoTargetsPanel } from '../WhoTargetsPanel';
import type { TargetsApiResponse } from '../../api/premium/types';

// Mock useTranslation
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => fallback || key,
  }),
}));

// Mock window.location.reload
const mockReload = vi.fn();
Object.defineProperty(window, 'location', {
  value: {
    reload: mockReload,
  },
  writable: true,
});

describe('WhoTargetsPanel', () => {
  const mockData: TargetsApiResponse = {
    calculation_date: '2024-01-15',
    kcal_daily: 2000,
    macros: {
      protein_g: 150,
      carbs_g: 250,
      fat_g: 67,
      fiber_g: 30,
    },
    water_ml: 2500,
    priority_micros: {
      iron: 18,
      calcium: 1000,
    },
    activity_weekly: {
      moderate_aerobic_min: 150,
      strength_sessions: 2,
      steps_daily: 10000,
    },
    warnings: [
      { message: 'Consider increasing protein intake' },
      { message: 'Monitor sodium levels' },
    ],
  };

  const defaultProps = {
    data: null,
    loading: false,
    error: null,
    onSaveAndContinue: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading State', () => {
    it('should render skeleton when loading', () => {
      render(<WhoTargetsPanel {...defaultProps} loading={true} />);

      expect(screen.getByText('WHO Nutrition Targets')).toBeInTheDocument();
      expect(document.querySelector('.who-targets-panel--loading')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should render error state with retry button', () => {
      const errorMessage = 'Failed to load targets';
      render(<WhoTargetsPanel {...defaultProps} error={errorMessage} />);

      expect(screen.getByText('WHO Nutrition Targets')).toBeInTheDocument();
      expect(screen.getByText('Unable to Calculate Targets')).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
      expect(screen.getByText('Try Again')).toBeInTheDocument();
    });

    it('should call window.location.reload when retry button is clicked and no onRetry prop', () => {
      const errorMessage = 'Network error';
      render(<WhoTargetsPanel {...defaultProps} error={errorMessage} />);

      const retryButton = screen.getByText('Try Again');
      fireEvent.click(retryButton);

      expect(mockReload).toHaveBeenCalledTimes(1);
    });

    it('should call onRetry prop when provided', () => {
      const onRetry = vi.fn();
      const errorMessage = 'API error';
      render(<WhoTargetsPanel {...defaultProps} error={errorMessage} onRetry={onRetry} />);

      const retryButton = screen.getByText('Try Again');
      fireEvent.click(retryButton);

      expect(onRetry).toHaveBeenCalledTimes(1);
      expect(mockReload).not.toHaveBeenCalled();
    });
  });

  describe('Empty State', () => {
    it('should render empty state when no data', () => {
      render(<WhoTargetsPanel {...defaultProps} data={null} />);

      expect(screen.getByText('WHO Nutrition Targets')).toBeInTheDocument();
      expect(screen.getByText('No Targets Available')).toBeInTheDocument();
      expect(screen.getByText('Please complete your profile to see personalized nutrition targets.')).toBeInTheDocument();
    });
  });

  describe('Loaded State', () => {
    it('should render all target data correctly', () => {
      render(<WhoTargetsPanel {...defaultProps} data={mockData} />);

      // Header
      expect(screen.getByText('WHO Nutrition Targets')).toBeInTheDocument();
      expect(screen.getByText('Personalized nutrition goals based on WHO guidelines')).toBeInTheDocument();

      // Daily Calories
      expect(screen.getByText('Daily Calories')).toBeInTheDocument();
      expect(screen.getByText('2,000')).toBeInTheDocument();
      expect(screen.getByText('kcal')).toBeInTheDocument();

      // Macronutrients
      expect(screen.getByText('Macronutrients')).toBeInTheDocument();
      expect(screen.getByText('Protein')).toBeInTheDocument();
      expect(screen.getByText('150g')).toBeInTheDocument();
      expect(screen.getByText('Carbs')).toBeInTheDocument();
      expect(screen.getByText('250g')).toBeInTheDocument();
      expect(screen.getByText('Fat')).toBeInTheDocument();
      expect(screen.getByText('67g')).toBeInTheDocument();
      expect(screen.getByText('Fiber')).toBeInTheDocument();
      expect(screen.getByText('30g')).toBeInTheDocument();

      // Hydration
      expect(screen.getByText('Hydration')).toBeInTheDocument();
      expect(screen.getByText('2,500')).toBeInTheDocument();
      expect(screen.getByText('ml')).toBeInTheDocument();

      // Priority Micronutrients
      expect(screen.getByText('Priority Micronutrients')).toBeInTheDocument();
      expect(screen.getByText('iron')).toBeInTheDocument();
      expect(screen.getByText('18')).toBeInTheDocument();
      expect(screen.getByText('calcium')).toBeInTheDocument();
      expect(screen.getByText('1,000')).toBeInTheDocument();

      // Activity Goals
      expect(screen.getByText('Activity Goals')).toBeInTheDocument();
      expect(screen.getByText('Moderate Aerobic')).toBeInTheDocument();
      expect(screen.getByText('150')).toBeInTheDocument();
      expect(screen.getByText('min/week')).toBeInTheDocument();
      expect(screen.getByText('Strength Training')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
      expect(screen.getByText('sessions/week')).toBeInTheDocument();
      expect(screen.getByText('Daily Steps')).toBeInTheDocument();
      expect(screen.getByText('10,000')).toBeInTheDocument();
      expect(screen.getByText('steps')).toBeInTheDocument();

      // Warnings
      expect(screen.getByText('Important Notes')).toBeInTheDocument();
      expect(screen.getByText('Consider increasing protein intake')).toBeInTheDocument();
      expect(screen.getByText('Monitor sodium levels')).toBeInTheDocument();

      // CTA Button
      expect(screen.getByText('Save & Get Weekly Plan')).toBeInTheDocument();
    });

    it('should call onSaveAndContinue when CTA button is clicked', () => {
      const onSaveAndContinue = vi.fn();
      render(<WhoTargetsPanel {...defaultProps} data={mockData} onSaveAndContinue={onSaveAndContinue} />);

      const ctaButton = screen.getByText('Save & Get Weekly Plan');
      fireEvent.click(ctaButton);

      expect(onSaveAndContinue).toHaveBeenCalledTimes(1);
    });

    it('should render without warnings when warnings array is empty', () => {
      const dataWithoutWarnings = { ...mockData, warnings: [] };
      render(<WhoTargetsPanel {...defaultProps} data={dataWithoutWarnings} />);

      expect(screen.queryByText('Important Notes')).not.toBeInTheDocument();
    });

    it('should render without priority micros when empty', () => {
      const dataWithoutMicros = { ...mockData, priority_micros: {} };
      render(<WhoTargetsPanel {...defaultProps} data={dataWithoutMicros} />);

      expect(screen.queryByText('Priority Micronutrients')).not.toBeInTheDocument();
    });

    it('should format numbers with proper localization', () => {
      const dataWithLargeNumbers = {
        ...mockData,
        kcal_daily: 1234567,
        macros: {
          protein_g: 123456,
          carbs_g: 234567,
          fat_g: 34567,
          fiber_g: 4567,
        },
        water_ml: 1234567,
        activity_weekly: {
          moderate_aerobic_min: 123456,
          strength_sessions: 1234,
          steps_daily: 1234567,
        },
      };

      render(<WhoTargetsPanel {...defaultProps} data={dataWithLargeNumbers} />);

      // Check that large numbers are properly formatted with commas
      expect(screen.getAllByText('1,234,567')).toHaveLength(3); // kcal_daily, water_ml, steps_daily
      expect(screen.getByText('123,456g')).toBeInTheDocument(); // protein_g
      expect(screen.getByText('234,567g')).toBeInTheDocument(); // carbs_g
      expect(screen.getByText('34,567g')).toBeInTheDocument(); // fat_g
      expect(screen.getByText('4,567g')).toBeInTheDocument(); // fiber_g
      expect(screen.getByText('123,456')).toBeInTheDocument(); // moderate_aerobic_min
      expect(screen.getByText('1,234')).toBeInTheDocument(); // strength_sessions
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA attributes for warnings', () => {
      render(<WhoTargetsPanel {...defaultProps} data={mockData} />);

      const warningIcons = document.querySelectorAll('.warning-item__icon[aria-hidden="true"]');
      expect(warningIcons).toHaveLength(2);
    });

    it('should have proper heading structure', () => {
      render(<WhoTargetsPanel {...defaultProps} data={mockData} />);

      const h2 = screen.getByRole('heading', { level: 2 });
      expect(h2).toHaveTextContent('WHO Nutrition Targets');

      const h3s = screen.getAllByRole('heading', { level: 3 });
      expect(h3s).toHaveLength(6); // Daily Calories, Macronutrients, Hydration, Priority Micronutrients, Activity Goals, Important Notes
    });
  });

  describe('Component States', () => {
    it('should apply correct CSS classes for different states', () => {
      const { rerender } = render(<WhoTargetsPanel {...defaultProps} loading={true} />);
      expect(document.querySelector('.who-targets-panel--loading')).toBeInTheDocument();

      rerender(<WhoTargetsPanel {...defaultProps} error="Test error" />);
      expect(document.querySelector('.who-targets-panel--error')).toBeInTheDocument();

      rerender(<WhoTargetsPanel {...defaultProps} data={null} />);
      expect(document.querySelector('.who-targets-panel--empty')).toBeInTheDocument();

      rerender(<WhoTargetsPanel {...defaultProps} data={mockData} />);
      expect(document.querySelector('.who-targets-panel--loaded')).toBeInTheDocument();
    });
  });
});

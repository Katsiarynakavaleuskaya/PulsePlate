import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WeeklyPlanReader } from '../WeeklyPlanReader';
import { getWeeklyPlan } from '../../../api/premium/weekly-plan';
import type { WeeklyMenuResponse } from '../../../api/premium/weekly-plan';
import type { TargetsRequest } from '../../../api/premium/types';

// Mock the API
vi.mock('../../../api/premium/weekly-plan', () => ({
  getWeeklyPlan: vi.fn(),
}));

const mockGetWeeklyPlan = vi.mocked(getWeeklyPlan);

// Mock data
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

const mockWeeklyPlanData: WeeklyMenuResponse = {
  week_summary: {},
  daily_menus: [
    {
      meals: {
        breakfast: [
          {
            name: 'Oatmeal with berries',
            calories: 300,
            protein: 12,
            carbs: 45,
            fat: 8,
            serving_size: '1 bowl',
            ingredients: ['oats', 'berries', 'milk']
          }
        ],
        lunch: [
          {
            name: 'Grilled chicken salad',
            calories: 400,
            protein: 35,
            carbs: 20,
            fat: 15,
            serving_size: '1 large bowl'
          }
        ],
        dinner: [
          {
            name: 'Salmon with vegetables',
            calories: 500,
            protein: 40,
            carbs: 25,
            fat: 20,
            serving_size: '1 fillet'
          }
        ]
      },
      total_calories: 1200,
      total_protein: 87,
      total_carbs: 90,
      total_fat: 43
    },
    // ... other days would be similar
  ],
  weekly_coverage: {
    protein: 95,
    carbs: 98,
    fat: 92,
    fiber: 85
  },
  shopping_list: {
    'chicken breast': 500,
    'salmon fillet': 300,
    'oats': 200,
    'berries': 150
  },
  total_cost: 45.50,
  adherence_score: 88
} as any;

describe('WeeklyPlanReader', () => {
  const user = userEvent.setup();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('Loading State', () => {
    it('should show loading skeleton when loading', () => {
      mockGetWeeklyPlan.mockImplementation(() => new Promise(() => {})); // Never resolves

      render(<WeeklyPlanReader request={mockRequest} />);

      expect(screen.getByTestId('weekly-plan-skeleton')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should show error state when API fails', async () => {
      const error = new Error('API Error');
      mockGetWeeklyPlan.mockRejectedValue(error);

      render(<WeeklyPlanReader request={mockRequest} />);

      await waitFor(() => {
        expect(screen.getByText('Failed to load weekly plan')).toBeInTheDocument();
      });

      expect(screen.getByText('API Error')).toBeInTheDocument();
      expect(screen.getByText('Try Again')).toBeInTheDocument();
    });

    it('should call onError callback when API fails', async () => {
      const error = new Error('API Error');
      const onError = vi.fn();
      mockGetWeeklyPlan.mockRejectedValue(error);

      render(<WeeklyPlanReader request={mockRequest} onError={onError} />);

      await waitFor(() => {
        expect(onError).toHaveBeenCalledWith(error);
      });
    });

    it('should retry when retry button is clicked', async () => {
      const error = new Error('API Error');
      mockGetWeeklyPlan.mockRejectedValueOnce(error);
      mockGetWeeklyPlan.mockResolvedValueOnce(mockWeeklyPlanData);

      render(<WeeklyPlanReader request={mockRequest} />);

      await waitFor(() => {
        expect(screen.getByText('Try Again')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Try Again'));

      await waitFor(() => {
        expect(screen.getByText('Weekly Meal Plan')).toBeInTheDocument();
      });
    });
  });

  describe('Empty State', () => {
    it('should show empty state when no data', async () => {
      mockGetWeeklyPlan.mockResolvedValue({
        week_summary: {},
        daily_menus: [],
        weekly_coverage: {},
        shopping_list: {},
        total_cost: 0,
        adherence_score: 0
      } as any);

      render(<WeeklyPlanReader request={mockRequest} />);

      await waitFor(() => {
        expect(screen.getByText('No weekly plan available')).toBeInTheDocument();
      });

      expect(screen.getByText('Generate Weekly Plan')).toBeInTheDocument();
    });
  });

  describe('Success State', () => {
    beforeEach(() => {
      mockGetWeeklyPlan.mockResolvedValue(mockWeeklyPlanData);
    });

    it('should render weekly plan when data is loaded', async () => {
      render(<WeeklyPlanReader request={mockRequest} />);

      await waitFor(() => {
        expect(screen.getByText('Weekly Meal Plan')).toBeInTheDocument();
      });

      expect(screen.getByText(/Week of/)).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: 'monday' })).toBeInTheDocument();
    });

    it('should display week coverage summary', async () => {
      render(<WeeklyPlanReader request={mockRequest} />);

      await waitFor(() => {
        expect(screen.getByText('Weekly Meal Plan')).toBeInTheDocument();
      });

      // Check week coverage values
      expect(screen.getByText('95%')).toBeInTheDocument();
      expect(screen.getByText('98%')).toBeInTheDocument();
      expect(screen.getByText('92%')).toBeInTheDocument();
      expect(screen.getByText('85%')).toBeInTheDocument();
    });

    it('should navigate between days', async () => {
      render(<WeeklyPlanReader request={mockRequest} />);

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: 'monday' })).toBeInTheDocument();
      });

      // Click next day
      await user.click(screen.getByLabelText('Next day'));
      expect(screen.getByRole('heading', { name: 'tuesday' })).toBeInTheDocument();

      // Click previous day
      await user.click(screen.getByLabelText('Previous day'));
      expect(screen.getByRole('heading', { name: 'monday' })).toBeInTheDocument();
    });

    it('should navigate to specific day when day button is clicked', async () => {
      render(<WeeklyPlanReader request={mockRequest} />);

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: 'monday' })).toBeInTheDocument();
      });

      // Click on Friday button
      await user.click(screen.getByRole('button', { name: 'friday' }));
      expect(screen.getByRole('heading', { name: 'friday' })).toBeInTheDocument();
    });

    it('should display meal information for current day', async () => {
      render(<WeeklyPlanReader request={mockRequest} />);

      await waitFor(() => {
        expect(screen.getByText('breakfast')).toBeInTheDocument();
      });

      expect(screen.getByText('Oatmeal with berries')).toBeInTheDocument();
      expect(screen.getAllByText('300 cal')).toHaveLength(2);
    });

    it('should display shopping list summary', async () => {
      render(<WeeklyPlanReader request={mockRequest} />);

      await waitFor(() => {
        expect(screen.getByText('Shopping List')).toBeInTheDocument();
      });

      // Check that shopping list section exists
      expect(screen.getByText('Shopping List')).toBeInTheDocument();
    });

    it('should display total calories for the day', async () => {
      render(<WeeklyPlanReader request={mockRequest} />);

      await waitFor(() => {
        expect(screen.getByText('Total Calories')).toBeInTheDocument();
      });

      expect(screen.getByText('1,200')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    beforeEach(() => {
      mockGetWeeklyPlan.mockResolvedValue(mockWeeklyPlanData);
    });

    it('should have proper ARIA labels for navigation buttons', async () => {
      render(<WeeklyPlanReader request={mockRequest} />);

      await waitFor(() => {
        expect(screen.getByLabelText('Previous day')).toBeInTheDocument();
        expect(screen.getByLabelText('Next day')).toBeInTheDocument();
      });
    });

    it('should support keyboard navigation', async () => {
      render(<WeeklyPlanReader request={mockRequest} />);

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: 'monday' })).toBeInTheDocument();
      });

      const nextButton = screen.getByLabelText('Next day');
      nextButton.focus();
      expect(nextButton).toHaveFocus();

      // Test Enter key activation
      fireEvent.keyDown(nextButton, { key: 'Enter' });
      expect(screen.getByRole('heading', { name: 'tuesday' })).toBeInTheDocument();
    });
  });

  describe('Props', () => {
    it('should not load data when no request is provided', () => {
      render(<WeeklyPlanReader />);

      expect(mockGetWeeklyPlan).not.toHaveBeenCalled();
      expect(screen.getByText('No weekly plan available')).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      render(<WeeklyPlanReader className="custom-class" />);

      expect(screen.getByText('No weekly plan available').closest('.weekly-plan-empty')).toHaveClass('custom-class');
    });
  });
});

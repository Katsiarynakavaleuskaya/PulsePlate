import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WeeklyPlanReader } from '../WeeklyPlanReader';
import { api } from '../../../api/client';
import type { WeeklyMenuResponse } from '../../../api/premium/weekly-plan';
import type { TargetsRequest } from '../../../api/premium/types';

// Mock the API client module (модульная система)
vi.mock('../../../api/client', () => ({
  api: vi.fn(),
}));

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (
      key: string,
      ...rest: Array<string | Record<string, unknown> | undefined>
    ) => {
      let fallback: string | undefined;
      let options: Record<string, unknown> | undefined;

      if (rest.length === 1) {
        const [arg] = rest;
        if (typeof arg === 'string') {
          fallback = arg;
        } else if (typeof arg === 'object' && arg !== null) {
          options = arg;
          if (typeof arg.defaultValue === 'string') {
            fallback = arg.defaultValue;
          }
        }
      } else if (rest.length >= 2) {
        const [maybeFallback, maybeOptions] = rest;
        if (typeof maybeFallback === 'string') {
          fallback = maybeFallback;
        }
        if (typeof maybeOptions === 'object' && maybeOptions !== null) {
          options = maybeOptions;
          if (!fallback && typeof maybeOptions.defaultValue === 'string') {
            fallback = maybeOptions.defaultValue;
          }
        }
      }

      if (options && typeof options.count === 'number') {
        return `${options.count} items`;
      }

      const translations: Record<string, string> = {
        'weeklyPlan.title': 'Weekly Meal Plan',
        'weeklyPlan.weekOf': 'Week of',
        'weeklyPlan.previousDay': 'Previous day',
        'weeklyPlan.nextDay': 'Next day',
        'weeklyPlan.protein': 'Protein',
        'weeklyPlan.carbs': 'Carbs',
        'weeklyPlan.fat': 'Fat',
        'weeklyPlan.fiber': 'Fiber',
        'weeklyPlan.shoppingList': 'Shopping List',
        'weeklyPlan.shoppingListItems': '{{count}} item',
        'weeklyPlan.dayMenuHeading': '{{day}} meals',
        'weeklyPlan.dayMenuLabel': 'Daily menu for {{day}}',
        'weeklyPlan.dayPosition': 'Day {{number}}',
        'weeklyPlan.dayNumber': 'Day {{number}}',
        'weeklyPlan.day': 'Day',
        'weeklyPlan.empty.title': 'No weekly plan available',
        'weeklyPlan.empty.message': 'Generate your personalized weekly meal plan to get started with your nutrition journey.',
        'weeklyPlan.empty.generate': 'Generate Weekly Plan',
        'weeklyPlan.empty.help': 'Complete your profile setup to generate a personalized meal plan.',
        'weeklyPlan.error.title': 'Failed to load weekly plan',
        'weeklyPlan.error.message': 'Something went wrong while loading your weekly meal plan.',
        'weeklyPlan.error.retry': 'Try Again',
        'weeklyPlan.error.help': 'If the problem persists, please check your internet connection and try again.',
        'units.kcal': 'kcal',
        'units.gram': 'g',
        'abbreviations.protein': 'P',
        'abbreviations.carbs': 'C',
        'abbreviations.fat': 'F',
      };

      if (key.includes('days.')) {
        const dayName = key.split('.').pop();
        return dayName ? dayName.charAt(0).toUpperCase() + dayName.slice(1) : key;
      }

      let template = translations[key] || fallback || key;

      if (typeof template === 'string' && options) {
        template = template.replace(/\{\{(\w+)\}\}/g, (_, token: string) => {
          const value = options?.[token];
          return value !== undefined ? String(value) : '';
        });
      }

      return template;
    },
    i18n: { language: 'en' },
  }),
}));

const mockApi = vi.mocked(api);

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
  week_summary: {
    week_start: '2025-01-06T00:00:00.000Z',
  },
  daily_menus: [
    {
      meals: [
        {
          title: 'Oatmeal with berries',
          title_translated: 'Oatmeal with berries',
          grams: { 'oats': 50, 'berries': 30, 'milk': 200 },
          kcal: 300,
          macros: { protein_g: 12, fat_g: 8, carbs_g: 45, fiber_g: 6 },
          micros: { 'fe': 2.5, 'ca': 150, 'k': 200 }
        },
        {
          title: 'Grilled chicken salad',
          title_translated: 'Grilled chicken salad',
          grams: { 'chicken': 150, 'lettuce': 100, 'tomato': 50 },
          kcal: 400,
          macros: { protein_g: 35, fat_g: 15, carbs_g: 20, fiber_g: 4 },
          micros: { 'fe': 3.2, 'ca': 80, 'k': 300 }
        },
        {
          title: 'Salmon with vegetables',
          title_translated: 'Salmon with vegetables',
          grams: { 'salmon': 120, 'broccoli': 100, 'carrots': 80 },
          kcal: 500,
          macros: { protein_g: 40, fat_g: 20, carbs_g: 25, fiber_g: 8 },
          micros: { 'fe': 4.1, 'ca': 120, 'k': 400 }
        }
      ],
      kcal: 1200,
      macros: { protein_g: 87, fat_g: 43, carbs_g: 90, fiber_g: 18 },
      micros: { 'fe': 9.8, 'ca': 350, 'k': 900 },
      coverage: { 'fe': 95, 'ca': 85, 'k': 90 },
      tips: ['Add more iron-rich foods', 'Consider calcium supplements'],
      total_cost: 15.50
    },
    ...Array.from({ length: 6 }, (_, i) => ({
      meals: [
        {
          title: `Breakfast Day ${i + 2}`,
          title_translated: `Breakfast Day ${i + 2}`,
          grams: { 'oats': 50, 'milk': 200, 'berries': 30 },
          kcal: 300,
          macros: { protein_g: 12, fat_g: 8, carbs_g: 45, fiber_g: 6 },
          micros: { 'fe': 2.5, 'ca': 150, 'k': 200 }
        },
        {
          title: `Lunch Day ${i + 2}`,
          title_translated: `Lunch Day ${i + 2}`,
          grams: { 'chicken': 150, 'rice': 100, 'vegetables': 80 },
          kcal: 400,
          macros: { protein_g: 35, fat_g: 15, carbs_g: 20, fiber_g: 4 },
          micros: { 'fe': 3.2, 'ca': 80, 'k': 300 }
        },
        {
          title: `Dinner Day ${i + 2}`,
          title_translated: `Dinner Day ${i + 2}`,
          grams: { 'fish': 120, 'potato': 100, 'salad': 50 },
          kcal: 500,
          macros: { protein_g: 40, fat_g: 20, carbs_g: 25, fiber_g: 8 },
          micros: { 'fe': 4.1, 'ca': 120, 'k': 400 }
        }
      ],
      kcal: 1200,
      macros: { protein_g: 87, fat_g: 43, carbs_g: 90, fiber_g: 18 },
      micros: { 'fe': 9.8, 'ca': 350, 'k': 900 },
      coverage: { 'fe': 95, 'ca': 85, 'k': 90 },
      tips: ['Add more iron-rich foods', 'Consider calcium supplements'],
      total_cost: 15.50
    }))
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
      mockApi.mockImplementation(() => new Promise(() => {})); // Never resolves

      render(<WeeklyPlanReader request={mockRequest} />);

      expect(screen.getByTestId('weekly-plan-skeleton')).toBeInTheDocument();
    });

    it('should ensure loading skeleton is accessible', () => {
      mockApi.mockImplementation(() => new Promise(() => {})); // Never resolves

      render(<WeeklyPlanReader request={mockRequest} />);

      const skeleton = screen.getByTestId('weekly-plan-skeleton');
      expect(skeleton).toHaveAttribute('role', 'status');
      expect(skeleton).toHaveAttribute('aria-label', 'Loading weekly plan');
    });
  });

  describe('Error State', () => {
    it('should show error state when API fails', async () => {
      const error = new Error('API Error');
      mockApi.mockRejectedValue(error);

      render(<WeeklyPlanReader request={mockRequest} />);

      await waitFor(() => {
        expect(screen.getByText('Failed to load weekly plan')).toBeInTheDocument();
      });

      expect(screen.getByText('API Error')).toBeInTheDocument();
      expect(screen.getByText('Try Again')).toBeInTheDocument();
    });

    it('should allow keyboard accessibility for the retry button in error state', async () => {
      const error = new Error('API Error');
      mockApi.mockRejectedValue(error);

      render(<WeeklyPlanReader request={mockRequest} />);

      await waitFor(() => {
        expect(screen.getByText('Failed to load weekly plan')).toBeInTheDocument();
      });

      const retryButton = screen.getByText('Try Again');
      retryButton.focus();
      expect(retryButton).toHaveFocus();

      // Simulate pressing Enter
      fireEvent.keyDown(retryButton, { key: 'Enter', code: 'Enter' });
      // Simulate pressing Space
      fireEvent.keyDown(retryButton, { key: ' ', code: 'Space' });

      // The button should remain focusable and accessible
      expect(retryButton).toHaveFocus();
    });

    it('should call onError callback when API fails', async () => {
      const error = new Error('API Error');
      const onError = vi.fn();
      mockApi.mockRejectedValue(error);

      render(<WeeklyPlanReader request={mockRequest} onError={onError} />);

      await waitFor(() => {
        expect(onError).toHaveBeenCalledWith(error);
      });
    });

    it('should retry when retry button is clicked', async () => {
      const error = new Error('API Error');
      mockApi.mockRejectedValueOnce(error);
      mockApi.mockResolvedValueOnce(mockWeeklyPlanData);

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
      mockApi.mockResolvedValue({
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
      mockApi.mockResolvedValue(mockWeeklyPlanData);
    });

    it('should render weekly plan when data is loaded', async () => {
      render(<WeeklyPlanReader request={mockRequest} />);

      await waitFor(() => {
        expect(screen.getByText('Weekly Meal Plan')).toBeInTheDocument();
      });

      expect(screen.getByText(/Week of/)).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: 'Monday meals' })).toBeInTheDocument();
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
        expect(screen.getByRole('heading', { name: 'Monday meals' })).toBeInTheDocument();
      });

      // Click next day
      await user.click(screen.getByLabelText('Next day'));
      expect(screen.getByRole('heading', { name: 'Tuesday meals' })).toBeInTheDocument();

      // Click previous day
      await user.click(screen.getByLabelText('Previous day'));
      expect(screen.getByRole('heading', { name: 'Monday meals' })).toBeInTheDocument();
    });

    it('should navigate to specific day when day button is clicked', async () => {
      render(<WeeklyPlanReader request={mockRequest} />);

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: 'Monday meals' })).toBeInTheDocument();
      });

      // Click on Friday button
      await user.click(screen.getByRole('button', { name: 'Friday' }));
      expect(screen.getByRole('heading', { name: 'Friday' })).toBeInTheDocument();
    });

    it('should display meal information for current day', async () => {
      render(<WeeklyPlanReader request={mockRequest} />);

      await waitFor(() => {
        expect(screen.getByText('Oatmeal with berries')).toBeInTheDocument();
      });

      expect(screen.getByText('Oatmeal with berries')).toBeInTheDocument();
      expect(screen.getAllByText('300 kcal')).toHaveLength(2);
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
        expect(screen.getByText('1,200 kcal')).toBeInTheDocument();
      });

      expect(screen.getByText('1,200 kcal')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    beforeEach(() => {
      mockApi.mockResolvedValue(mockWeeklyPlanData);
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
        expect(screen.getByRole('heading', { name: 'Monday meals' })).toBeInTheDocument();
      });

      const nextButton = screen.getByLabelText('Next day');
      nextButton.focus();
      expect(nextButton).toHaveFocus();

      // Test Enter key activation
      fireEvent.keyDown(nextButton, { key: 'Enter' });
      expect(screen.getByRole('heading', { name: 'Tuesday meals' })).toBeInTheDocument();
    });

    it('should wrap keyboard navigation from Sunday to Monday and back', async () => {
      render(<WeeklyPlanReader request={mockRequest} />);

      // Start at Monday (index 0)
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: 'Monday meals' })).toBeInTheDocument();
      });

      const prevButton = screen.getByLabelText('Previous day');
      prevButton.focus();

      // Navigate backward through the week by pressing "Previous day" 6 times (Monday -> Tuesday)
      for (let i = 0; i < 6; i++) {
        fireEvent.keyDown(prevButton, { key: 'Enter' });
      }
      expect(screen.getByRole('heading', { name: 'Tuesday meals' })).toBeInTheDocument();

      // Press "Next day" to wrap to Wednesday
      const nextButton = screen.getByLabelText('Next day');
      nextButton.focus();
      fireEvent.keyDown(nextButton, { key: 'Enter' });
      expect(screen.getByRole('heading', { name: 'Wednesday meals' })).toBeInTheDocument();

      // Press "Previous day" to wrap back to Sunday
      prevButton.focus();
      fireEvent.keyDown(prevButton, { key: 'Enter' });
      expect(screen.getByRole('heading', { name: 'Tuesday meals' })).toBeInTheDocument();
    });
  });

  describe('Props', () => {
    it('should not load data when no request is provided', () => {
      render(<WeeklyPlanReader />);

      expect(mockApi).not.toHaveBeenCalled();
      expect(screen.getByText('No weekly plan available')).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      render(<WeeklyPlanReader className="custom-class" />);

      expect(screen.getByTestId('weekly-plan-empty')).toHaveClass('custom-class');
    });
  });
});

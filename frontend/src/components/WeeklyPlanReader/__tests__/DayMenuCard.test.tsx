import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DayMenuCard } from '../DayMenuCard';

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => {
      const translations: Record<string, string> = {
        'weeklyPlan.totalCalories': 'Total Calories',
        'weeklyPlan.protein': 'Protein',
        'weeklyPlan.carbs': 'Carbs',
        'weeklyPlan.fat': 'Fat',
        'weeklyPlan.meals.breakfast': 'Breakfast',
        'weeklyPlan.meals.lunch': 'Lunch',
        'weeklyPlan.meals.dinner': 'Dinner',
        'weeklyPlan.meals.snacks': 'Snacks',
        'weeklyPlan.meals.misc': 'Other Meals',
        'weeklyPlan.noMeals': 'No meals planned for this day',
      };
      return translations[key] || fallback || key;
    },
  }),
}));

describe('DayMenuCard', () => {
  it('should categorize meals by explicit meal_type field', () => {
    const dayData = {
      meals: [
        {
          title: 'Oatmeal',
          title_translated: 'Oatmeal',
          grams: { 'oats': 50, 'milk': 200 } as { [key: string]: number },
          kcal: 300,
          macros: { protein_g: 12, fat_g: 8, carbs_g: 45, fiber_g: 6 },
          micros: { 'fe': 2.5, 'ca': 150, 'k': 200 },
          meal_type: 'breakfast'
        },
        {
          title: 'Salad',
          title_translated: 'Salad',
          grams: { 'lettuce': 100, 'tomato': 50 } as { [key: string]: number },
          kcal: 250,
          macros: { protein_g: 8, fat_g: 5, carbs_g: 30, fiber_g: 4 },
          micros: { 'fe': 1.5, 'ca': 80, 'k': 150 },
          meal_type: 'lunch'
        },
        {
          title: 'Chicken',
          title_translated: 'Chicken',
          grams: { 'chicken': 150 } as { [key: string]: number },
          kcal: 400,
          macros: { protein_g: 35, fat_g: 15, carbs_g: 20, fiber_g: 4 },
          micros: { 'fe': 3.2, 'ca': 80, 'k': 300 },
          meal_type: 'dinner'
        },
        {
          title: 'Apple',
          title_translated: 'Apple',
          grams: { 'apple': 120 } as { [key: string]: number },
          kcal: 80,
          macros: { protein_g: 0.5, fat_g: 0.3, carbs_g: 20, fiber_g: 3 },
          micros: { 'fe': 0.2, 'ca': 10, 'k': 100 },
          meal_type: 'snacks'
        },
        {
          title: 'Protein Shake',
          title_translated: 'Protein Shake',
          grams: { 'protein_powder': 30, 'water': 250 } as { [key: string]: number },
          kcal: 150,
          macros: { protein_g: 25, fat_g: 2, carbs_g: 5, fiber_g: 1 },
          micros: { 'fe': 1.0, 'ca': 50, 'k': 50 },
          meal_type: 'misc'
        },
      ],
      total_nutrients: {
        calories: 1180,
        protein: 60,
        carbs: 120,
        fat: 30,
      },
    };

    render(<DayMenuCard day="Monday" dayData={dayData} dayIndex={0} />);

    // Check that meals are categorized correctly
    expect(screen.getByText('Breakfast')).toBeInTheDocument();
    expect(screen.getByText('Lunch')).toBeInTheDocument();
    expect(screen.getByText('Dinner')).toBeInTheDocument();
    expect(screen.getByText('Snacks')).toBeInTheDocument();
    expect(screen.getByText('Other Meals')).toBeInTheDocument();

    // Check that specific meals appear in their correct categories
    expect(screen.getByText('Oatmeal')).toBeInTheDocument();
    expect(screen.getByText('Salad')).toBeInTheDocument();
    expect(screen.getByText('Chicken')).toBeInTheDocument();
    expect(screen.getByText('Apple')).toBeInTheDocument();
    expect(screen.getByText('Protein Shake')).toBeInTheDocument();
  });

  it('should use positional fallback for meals without meal_type', () => {
    const dayData = {
      meals: [
        {
          title: 'Oatmeal',
          title_translated: 'Oatmeal',
          grams: { 'oats': 50, 'milk': 200 } as { [key: string]: number },
          kcal: 300,
          macros: { protein_g: 12, fat_g: 8, carbs_g: 45, fiber_g: 6 },
          micros: { 'fe': 2.5, 'ca': 150, 'k': 200 }
        }, // No meal_type - should go to breakfast
        {
          title: 'Salad',
          title_translated: 'Salad',
          grams: { 'lettuce': 100, 'tomato': 50 } as { [key: string]: number },
          kcal: 250,
          macros: { protein_g: 8, fat_g: 5, carbs_g: 30, fiber_g: 4 },
          micros: { 'fe': 1.5, 'ca': 80, 'k': 150 }
        },   // No meal_type - should go to lunch
        {
          title: 'Chicken',
          title_translated: 'Chicken',
          grams: { 'chicken': 150 } as { [key: string]: number },
          kcal: 400,
          macros: { protein_g: 35, fat_g: 15, carbs_g: 20, fiber_g: 4 },
          micros: { 'fe': 3.2, 'ca': 80, 'k': 300 }
        }, // No meal_type - should go to dinner
        {
          title: 'Apple',
          title_translated: 'Apple',
          grams: { 'apple': 120 } as { [key: string]: number },
          kcal: 80,
          macros: { protein_g: 0.5, fat_g: 0.3, carbs_g: 20, fiber_g: 3 },
          micros: { 'fe': 0.2, 'ca': 10, 'k': 100 }
        },    // No meal_type - should go to snacks
        {
          title: 'Extra Meal',
          title_translated: 'Extra Meal',
          grams: { 'extra': 100 } as { [key: string]: number },
          kcal: 150,
          macros: { protein_g: 10, fat_g: 5, carbs_g: 15, fiber_g: 2 },
          micros: { 'fe': 1.0, 'ca': 30, 'k': 80 }
        }, // Beyond initial sequence - should go to misc
      ],
      total_nutrients: {
        calories: 1180,
      },
    };

    render(<DayMenuCard day="Tuesday" dayData={dayData} dayIndex={1} />);

    // Check that meals are categorized using positional fallback
    expect(screen.getByText('Breakfast')).toBeInTheDocument();
    expect(screen.getByText('Lunch')).toBeInTheDocument();
    expect(screen.getByText('Dinner')).toBeInTheDocument();
    expect(screen.getByText('Snacks')).toBeInTheDocument();
    expect(screen.getByText('Other Meals')).toBeInTheDocument();
  });

  it('should handle invalid meal items gracefully', () => {
    const dayData = {
      meals: [
        {
          title: 'Valid Meal',
          title_translated: 'Valid Meal',
          grams: { 'food': 100 } as { [key: string]: number },
          kcal: 300,
          macros: { protein_g: 15, fat_g: 10, carbs_g: 30, fiber_g: 5 },
          micros: { 'fe': 2.0, 'ca': 100, 'k': 200 },
          meal_type: 'breakfast'
        },
        {
          title: '',
          title_translated: '',
          grams: { 'food': 100 } as { [key: string]: number },
          kcal: 250,
          macros: { protein_g: 10, fat_g: 8, carbs_g: 25, fiber_g: 3 },
          micros: { 'fe': 1.5, 'ca': 80, 'k': 150 }
        }, // Invalid: empty name
        null, // Invalid: null item
        {
          title: 'Another Valid Meal',
          title_translated: 'Another Valid Meal',
          grams: { 'food': 150 } as { [key: string]: number },
          kcal: 400,
          macros: { protein_g: 20, fat_g: 15, carbs_g: 40, fiber_g: 6 },
          micros: { 'fe': 3.0, 'ca': 120, 'k': 250 },
          meal_type: 'lunch'
        },
      ] as any, // Type assertion to allow null values for testing
      total_nutrients: {
        calories: 700,
      },
    };

    render(<DayMenuCard day="Wednesday" dayData={dayData} dayIndex={2} />);

    // Should only show valid meals
    expect(screen.getByText('Valid Meal')).toBeInTheDocument();
    expect(screen.getByText('Another Valid Meal')).toBeInTheDocument();
    // Invalid meals should not appear
    expect(screen.queryByText('Invalid Meal')).not.toBeInTheDocument();
  });

  it('should display total calories correctly', () => {
    const dayData = {
      meals: [
        {
          title: 'Oatmeal',
          title_translated: 'Oatmeal',
          grams: { 'oats': 50, 'milk': 200 } as { [key: string]: number },
          kcal: 300,
          macros: { protein_g: 12, fat_g: 8, carbs_g: 45, fiber_g: 6 },
          micros: { 'fe': 2.5, 'ca': 150, 'k': 200 },
          meal_type: 'breakfast'
        },
        {
          title: 'Salad',
          title_translated: 'Salad',
          grams: { 'lettuce': 100, 'tomato': 50 } as { [key: string]: number },
          kcal: 250,
          macros: { protein_g: 8, fat_g: 5, carbs_g: 30, fiber_g: 4 },
          micros: { 'fe': 1.5, 'ca': 80, 'k': 150 },
          meal_type: 'lunch'
        },
      ],
      total_nutrients: {
        calories: 550,
        protein: 25,
        carbs: 60,
        fat: 15,
      },
    };

    render(<DayMenuCard day="Thursday" dayData={dayData} dayIndex={3} />);

    expect(screen.getByText('550')).toBeInTheDocument(); // Total calories
    expect(screen.getByText('25g')).toBeInTheDocument(); // Protein
    expect(screen.getByText('60g')).toBeInTheDocument(); // Carbs
    expect(screen.getByText('15g')).toBeInTheDocument(); // Fat
  });

  it('should show no meals message when no meals are provided', () => {
    const dayData = {
      meals: [],
      total_nutrients: {
        calories: 0,
      },
    };

    render(<DayMenuCard day="Friday" dayData={dayData} dayIndex={4} />);

    expect(screen.getByText('No meals planned for this day')).toBeInTheDocument();
  });
});

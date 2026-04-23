/** @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { SettingsProvider } from '../../../lib/settings';
import NutritionSetupPage from '../index';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    i18n: { language: 'en' },
    t: (key: string) => key,
  }),
}));

vi.mock('../hooks', () => ({
  resolveSetupLang: vi.fn(() => 'en'),
  useSetupCalc: vi.fn(() => ({
    bmrData: { bmr: 1400, tdee: 1800, method: 'Mifflin-St Jeor' },
    plateData: {
      plate: { carbs_pct: 50, protein_pct: 25, fat_pct: 25, kcal: 1800 },
      macros: { carbs_g: 200, protein_g: 120, fat_g: 60, fiber_g: 30 },
      water_l: 2.4,
    },
    loading: false,
    error: null,
  })),
  useTargets: vi.fn(() => ({
    data: { micros: [], water_l: 2.4 },
    loading: false,
    error: null,
  })),
}));

describe('NutritionSetupPage', () => {
  it('moves the governed stepper from profile to results after submit', async () => {
    const user = userEvent.setup();

    render(
      <SettingsProvider>
        <NutritionSetupPage />
      </SettingsProvider>
    );

    expect(screen.getByText('Step 1 of 2')).toBeInTheDocument();
    expect(screen.getByRole('listitem', { current: 'step' })).toHaveTextContent('Profile');

    await user.click(screen.getByRole('button', { name: 'nutritionSetup.calculateButton' }));

    await waitFor(() => {
      expect(screen.getByText('Step 2 of 2')).toBeInTheDocument();
    });

    expect(screen.getByRole('listitem', { current: 'step' })).toHaveTextContent('Results');
  });
});

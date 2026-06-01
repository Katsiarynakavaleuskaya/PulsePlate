/** @vitest-environment jsdom */
import { useEffect, useRef, type ReactNode } from 'react';
import '@testing-library/jest-dom/vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { SettingsProvider, useSettings, type Settings } from '../../../lib/settings';
import NutritionSetupPage from '../index';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    i18n: { language: 'en' },
    t: (key: string, values?: Record<string, number>) => {
      if (key === 'nutritionSetup.steps.progressLabel') {
        return `Step ${values?.current} of ${values?.total}`;
      }
      return key;
    },
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
    enabled: true,
  })),
  useTargets: vi.fn(() => ({
    data: { micros: [], water_l: 2.4 },
    loading: false,
    error: null,
  })),
}));

function SeedSettings({
  children,
  guidedPlanningDraft,
}: {
  children: ReactNode;
  guidedPlanningDraft?: Settings['guidedPlanningDraft'];
}) {
  return (
    <SettingsProvider>
      <MemoryRouter>
        <SettingsSeed guidedPlanningDraft={guidedPlanningDraft}>{children}</SettingsSeed>
      </MemoryRouter>
    </SettingsProvider>
  );
}

function SettingsSeed({
  children,
  guidedPlanningDraft,
}: {
  children: ReactNode;
  guidedPlanningDraft?: Settings['guidedPlanningDraft'];
}) {
  const { updateSetting } = useSettings();
  const didSeed = useRef(false);

  useEffect(() => {
    if (didSeed.current) {
      return;
    }
    if (guidedPlanningDraft !== undefined) {
      updateSetting('guidedPlanningDraft', guidedPlanningDraft);
    }
    didSeed.current = true;
  }, [guidedPlanningDraft, updateSetting]);

  return <>{children}</>;
}

describe('NutritionSetupPage', () => {
  it('moves the governed stepper from profile to results after submit', async () => {
    const user = userEvent.setup();

    render(
      <SettingsProvider>
        <NutritionSetupPage />
      </SettingsProvider>
    );

    expect(screen.getByText('Step 1 of 2')).toBeInTheDocument();
    expect(screen.getByRole('listitem', { current: 'step' })).toHaveTextContent('nutritionSetup.steps.profile.label');

    await user.click(screen.getByRole('button', { name: 'nutritionSetup.calculateButton' }));

    await waitFor(() => {
      expect(screen.getByText('Step 2 of 2')).toBeInTheDocument();
    });

    expect(screen.getByRole('listitem', { current: 'step' })).toHaveTextContent('nutritionSetup.steps.results.label');
  });

  it('shows planning direction from a valid guided planning draft and carries it to results', async () => {
    const user = userEvent.setup();

    render(
      <SeedSettings
        guidedPlanningDraft={{
          intentId: 'shopping',
          timeId: 'batch',
          savedAt: '2026-06-01T00:00:00.000Z',
        }}
      >
        <NutritionSetupPage />
      </SeedSettings>
    );

    expect(await screen.findByTestId('planning-direction-panel')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Shopping-list planning' })).toBeInTheDocument();
    expect(screen.getByText('Batch prep')).toBeInTheDocument();
    expect(screen.getByText(/Translate check-in intent into meal anchors/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'nutritionSetup.calculateButton' }));

    await waitFor(() => {
      expect(screen.getByRole('navigation', { name: 'Guided planning next steps' })).toBeInTheDocument();
    });

    expect(screen.getByRole('link', { name: 'Continue to plate' })).toHaveAttribute('href', '/plate');
    expect(screen.getByRole('link', { name: 'Open progress check-ins' })).toHaveAttribute('href', '/progress');
  });

  it('does not show planning direction when the guided planning draft is invalid', () => {
    render(
      <SeedSettings
        guidedPlanningDraft={
          {
            intentId: 'invalid-intent',
            timeId: 'batch',
            savedAt: '2026-06-01T00:00:00.000Z',
          } as unknown as Settings['guidedPlanningDraft']
        }
      >
        <NutritionSetupPage />
      </SeedSettings>
    );

    expect(screen.queryByTestId('planning-direction-panel')).not.toBeInTheDocument();
  });
});

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import BMICalculatePage from '../BMICalculatePage';

vi.mock('../../../api/bmi', () => ({
  calculateBMI: vi.fn(),
}));

vi.mock('../../../components/SoftPaywallHook', () => ({
  default: () => <div data-testid="soft-paywall-hook">soft paywall</div>,
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        'bmiCalculate.title': 'BMI Calculator',
        'bmiCalculate.description': 'Calculate your Body Mass Index',
        'bmiCalculate.form.weightLabel': 'Weight (kg)',
        'bmiCalculate.form.heightLabel': 'Height (cm)',
        'bmiCalculate.form.ageLabel': 'Age',
        'bmiCalculate.form.waistLabel': 'Waist (cm, optional)',
        'bmiCalculate.form.sexLabel': 'Sex',
        'bmiCalculate.form.sex.male': 'Male',
        'bmiCalculate.form.sex.female': 'Female',
        'bmiCalculate.form.athleteLabel': 'Athlete (optional)',
        'bmiCalculate.form.pregnantLabel': 'Pregnant (optional)',
        'bmiCalculate.form.submit': 'Calculate BMI',
        'bmiCalculate.form.submitting': 'Please wait',
        'bmiCalculate.form.reset': 'Calculate Again',
        'bmiCalculate.result.title': 'BMI Result',
        'bmiCalculate.error.invalidWeight': 'Please enter a valid weight (kg).',
        'bmiCalculate.error.invalidHeight': 'Please enter a valid height (cm).',
        'bmiCalculate.error.invalidAge': 'Please enter a valid age (1-120 years).',
        'bmiCalculate.error.generic': 'An error occurred. Please try again.',
      })[key] ?? key,
    i18n: { language: 'en' },
  }),
}));

import { calculateBMI } from '../../../api/bmi';

describe('BMICalculatePage', () => {
  beforeEach(() => {
    vi.mocked(calculateBMI).mockReset();
  });

  it('renders the redesigned BMI surface', () => {
    render(<BMICalculatePage />);

    expect(screen.getByRole('heading', { level: 1, name: 'BMI Calculator' })).toBeInTheDocument();
    expect(screen.getByText('Weight')).toBeInTheDocument();
    expect(screen.getByText('Height')).toBeInTheDocument();
    expect(screen.getByText('Age + context')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Calculate BMI' })).toBeDisabled();
  });

  it('submits valid values and renders the result rail', async () => {
    vi.mocked(calculateBMI).mockResolvedValue({
      bmi: 22.4,
      category: 'Balanced zone',
      interpretation: 'Your body composition looks healthy.',
      soft_paywall: null,
    } as Awaited<ReturnType<typeof calculateBMI>>);

    const user = userEvent.setup();
    render(<BMICalculatePage />);

    await user.type(screen.getByLabelText('Weight (kg)'), '70');
    await user.type(screen.getByLabelText('Height (cm)'), '177');
    await user.type(screen.getByLabelText('Age'), '31');
    await user.click(screen.getByRole('button', { name: 'Calculate BMI' }));

    expect(vi.mocked(calculateBMI)).toHaveBeenCalled();
    expect(await screen.findByText('22.4')).toBeInTheDocument();
    expect(screen.getByText('Your body composition looks healthy.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Calculate Again' })).toBeInTheDocument();
  });
});

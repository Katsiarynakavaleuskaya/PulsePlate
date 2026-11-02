import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import SetupForm from '../SetupForm';
import NutritionSetupPage from '../index';
import { parseSetupFormValues, setupSchema, validDietFlags, type SetupFormValues } from '../schema';
import * as setupHooks from '../hooks';
import * as settingsModule from '../../../lib/settings';
import { SettingsProvider } from '../../../lib/settings';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    i18n: { language: 'en' },
    t: (key: string) => key,
  }),
}));

vi.mock('../hooks', () => ({
  resolveSetupLang: vi.fn(() => 'en'),
  useSetupCalc: vi.fn(() => ({
    bmrData: null,
    plateData: null,
    loading: true,
    error: null,
    enabled: true,
  })),
  useTargets: vi.fn(() => ({ data: null, loading: true, error: null })),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

const validSetupInput = {
  sex: 'female',
  age: 30,
  height_cm: 170,
  weight_kg: 65,
  activity: 'moderate',
  goal: 'maintain',
} as const;

describe('SetupForm', () => {
  it.each([
    { height: '170,5', weight: '65,4' },
    { height: '170.5', weight: '65.4' },
  ])('normalizes decimal inputs $height and $weight before submit', async ({ height, weight }) => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();

    render(
      <SettingsProvider>
        <SetupForm onSubmit={onSubmit} />
      </SettingsProvider>
    );

    await user.clear(screen.getByPlaceholderText('30'));
    await user.type(screen.getByPlaceholderText('30'), '30');
    await user.clear(screen.getByPlaceholderText('170'));
    await user.type(screen.getByPlaceholderText('170'), height);
    await user.clear(screen.getByPlaceholderText('65'));
    await user.type(screen.getByPlaceholderText('65'), weight);
    await user.click(screen.getByRole('button', { name: 'nutritionSetup.calculateButton' }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          age: 30,
          height_cm: 170.5,
          weight_kg: 65.4,
        })
      );
    });
  });

  it.each(['30,9', '30.9'])('rejects fractional age %s instead of truncating it', async (age) => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();

    render(
      <SettingsProvider>
        <SetupForm onSubmit={onSubmit} />
      </SettingsProvider>
    );

    await user.clear(screen.getByPlaceholderText('30'));
    await user.type(screen.getByPlaceholderText('30'), age);
    await user.click(screen.getByRole('button', { name: 'nutritionSetup.calculateButton' }));

    expect(await screen.findByText('Expected integer, received float')).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('submits parsed defaults and all existing checkbox choices without duplicates', async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<SettingsProvider><SetupForm onSubmit={onSubmit} /></SettingsProvider>);

    await user.click(screen.getByRole('button', { name: 'nutritionSetup.calculateButton' }));
    await waitFor(() => expect(onSubmit).toHaveBeenLastCalledWith({ ...validSetupInput, diet_flags: [] }));

    const boxes = screen.getAllByRole('checkbox');
    expect(boxes).toHaveLength(validDietFlags.length);
    for (const box of boxes) await user.click(box);
    await user.click(boxes[0]);
    await user.click(boxes[0]);
    await user.click(screen.getByRole('button', { name: 'nutritionSetup.calculateButton' }));
    await waitFor(() => {
      const values = onSubmit.mock.calls[onSubmit.mock.calls.length - 1]?.[0];
      expect(values).toEqual({ ...validSetupInput, diet_flags: expect.arrayContaining([...validDietFlags]) });
      expect(values.diet_flags).toHaveLength(validDietFlags.length);
      expect(new Set(values.diet_flags).size).toBe(validDietFlags.length);
    });
  });

  it.each([
    ['30', '', 'Required'],
    ['30', 'abc', 'Required'],
    ['170', 'Infinity', 'Required'],
    ['65', 'NaN', 'Required'],
    ['30', '12', 'Number must be greater than or equal to 13'],
    ['30', '91', 'Number must be less than or equal to 90'],
    ['170', '119', 'Number must be greater than or equal to 120'],
    ['170', '231', 'Number must be less than or equal to 230'],
    ['65', '29', 'Number must be greater than or equal to 30'],
    ['65', '301', 'Number must be less than or equal to 300'],
  ])('rejects numeric input %s=%s with its visible error', async (placeholder, input, message) => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<SettingsProvider><SetupForm onSubmit={onSubmit} /></SettingsProvider>);
    await user.clear(screen.getByPlaceholderText(placeholder));
    if (input) await user.type(screen.getByPlaceholderText(placeholder), input);
    await user.click(screen.getByRole('button', { name: 'nutritionSetup.calculateButton' }));
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });
});

describe('Nutrition Setup parsed input boundary', () => {
  it('returns normalized output without mutating omitted flags or unknown raw fields', () => {
    const raw = Object.freeze({ ...validSetupInput, legacy_note: 'preserve raw input' });
    expect(parseSetupFormValues(raw)).toEqual({ ...validSetupInput, diet_flags: [] });
    expect(raw).not.toHaveProperty('diet_flags');
    expect(raw.legacy_note).toBe('preserve raw input');
  });

  it.each([{ flags: [] }, { flags: [...validDietFlags] }, { flags: ['VEG', 'VEG'] }])('preserves valid bounded flags $flags', ({ flags }) => {
    expect(parseSetupFormValues({ ...validSetupInput, diet_flags: flags })).toEqual({
      ...validSetupInput, diet_flags: flags,
    });
  });

  it('rejects eleven invalid flags before reading elements, and still validates a small array', () => {
    let reads = 0;
    const counted = (length: number): string[] => {
      const values = new Array<string>(length);
      for (let index = 0; index < length; index += 1) {
        Object.defineProperty(values, index, {
          enumerable: true,
          get(): string { reads += 1; return 'INVALID_FLAG'; },
        });
      }
      return values;
    };
    const oversized = setupSchema.safeParse({ ...validSetupInput, diet_flags: counted(validDietFlags.length + 1) });
    expect(reads).toBe(0);
    expect(oversized.success).toBe(false);
    if (oversized.success) throw new Error('Oversized flags unexpectedly parsed');
    expect(oversized.error.issues).toEqual([
      expect.objectContaining({ code: 'too_big', maximum: validDietFlags.length, path: ['diet_flags'] }),
    ]);

    const small = setupSchema.safeParse({ ...validSetupInput, diet_flags: counted(1) });
    expect(reads).toBe(1);
    expect(small.success).toBe(false);
    if (small.success) throw new Error('Invalid flag unexpectedly parsed');
    expect(small.error.issues).toEqual([
      expect.objectContaining({ code: 'invalid_value', path: ['diet_flags', 0] }),
    ]);
  });
});

describe('Nutrition Setup page restoration', () => {
  it('keeps one parsed-output identity after a form submit', async () => {
    render(<SettingsProvider><MemoryRouter><NutritionSetupPage /></MemoryRouter></SettingsProvider>);
    const form = screen.getByRole('button', { name: 'nutritionSetup.calculateButton' }).closest('form');
    if (!form) throw new Error('Setup form is missing');
    await act(async () => {
      fireEvent.submit(form);
    });
    await waitFor(() => expect(setupHooks.useSetupCalc).toHaveBeenCalled());
    const delivered = vi.mocked(setupHooks.useSetupCalc).mock.calls.map(([values]) => values);
    expect(new Set(delivered).size).toBe(1);
    expect(delivered[0]).toEqual({ ...validSetupInput, diet_flags: [] });
  });

  it('passes real parsed defaults to ResultView hooks and leaves raw saved settings untouched', async () => {
    const raw = Object.freeze({ ...validSetupInput, legacy_note: 'keep me' });
    // A deliberately untrusted saved-data fixture crosses the typed context only here.
    vi.spyOn(settingsModule, 'useSettings').mockReturnValue({
      settings: { setup: raw as unknown as SetupFormValues },
      updateSetting: vi.fn(),
    });
    render(<MemoryRouter><NutritionSetupPage /></MemoryRouter>);
    await waitFor(() => expect(setupHooks.useSetupCalc).toHaveBeenCalled());
    const calculationCalls = vi.mocked(setupHooks.useSetupCalc).mock.calls;
    const restored = calculationCalls[calculationCalls.length - 1]?.[0];
    expect(restored).toEqual({ ...validSetupInput, diet_flags: [] });
    expect(restored).not.toBe(raw);
    const targetCalls = vi.mocked(setupHooks.useTargets).mock.calls;
    expect(targetCalls[targetCalls.length - 1]?.[0]).toEqual(restored);
    expect(raw).toEqual({ ...validSetupInput, legacy_note: 'keep me' });
    expect(raw).not.toHaveProperty('diet_flags');
    expect(screen.getByRole('listitem', { current: 'step' })).toHaveTextContent('nutritionSetup.steps.results.label');
  });

  it('keeps invalid saved data on the form without passing it to result hooks', async () => {
    const raw = Object.freeze({ ...validSetupInput, weight_kg: 'invalid', legacy_note: 'keep me' });
    // The production context and output types remain strict; only this corrupt-data fixture is bridged.
    vi.spyOn(settingsModule, 'useSettings').mockReturnValue({
      settings: { setup: raw as unknown as SetupFormValues },
      updateSetting: vi.fn(),
    });
    render(<MemoryRouter><NutritionSetupPage /></MemoryRouter>);
    expect(await screen.findByRole('button', { name: 'nutritionSetup.calculateButton' })).toBeInTheDocument();
    expect(screen.getByRole('listitem', { current: 'step' })).toHaveTextContent('nutritionSetup.steps.profile.label');
    expect(setupHooks.useSetupCalc).not.toHaveBeenCalled();
    expect(setupHooks.useTargets).not.toHaveBeenCalled();
    expect(raw).toEqual({ ...validSetupInput, weight_kg: 'invalid', legacy_note: 'keep me' });
  });
});

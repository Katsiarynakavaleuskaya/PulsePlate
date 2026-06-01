import { describe, it, expect, vi } from 'vitest';
import { render, screen, renderHook, act } from '@testing-library/react';
import { SettingsProvider, useSettings, type Settings } from '../settings';

const setupValues: NonNullable<Settings['setup']> = {
  sex: 'female',
  age: 34,
  height_cm: 168,
  weight_kg: 64,
  activity: 'moderate',
  goal: 'maintain',
  diet_flags: ['HIGH_PROTEIN'],
};

describe('SettingsProvider', () => {
  it('renders children', () => {
    render(
      <SettingsProvider>
        <div>Test Content</div>
      </SettingsProvider>
    );

    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('provides initial empty settings', () => {
    const { result } = renderHook(() => useSettings(), {
      wrapper: SettingsProvider,
    });

    expect(result.current.settings).toEqual({});
  });

  it('stores setup form values in memory', () => {
    const { result } = renderHook(() => useSettings(), {
      wrapper: SettingsProvider,
    });

    act(() => {
      result.current.updateSetting('setup', setupValues);
    });

    expect(result.current.settings).toEqual({ setup: setupValues });
  });

  it('stores and overwrites a guided planning draft in memory', () => {
    const { result } = renderHook(() => useSettings(), {
      wrapper: SettingsProvider,
    });

    act(() => {
      result.current.updateSetting('guidedPlanningDraft', {
        intentId: 'consistent',
        timeId: 'standard',
        savedAt: '2026-06-01T00:00:00.000Z',
      });
      result.current.updateSetting('guidedPlanningDraft', {
        intentId: 'shopping',
        timeId: 'batch',
        savedAt: '2026-06-01T00:01:00.000Z',
      });
    });

    expect(result.current.settings.guidedPlanningDraft).toEqual({
      intentId: 'shopping',
      timeId: 'batch',
      savedAt: '2026-06-01T00:01:00.000Z',
    });
  });

  it('allows clearing the guided planning draft without persistence', () => {
    const { result } = renderHook(() => useSettings(), {
      wrapper: SettingsProvider,
    });

    act(() => {
      result.current.updateSetting('guidedPlanningDraft', {
        intentId: 'balanced',
        timeId: 'quick',
      });
      result.current.updateSetting('guidedPlanningDraft', undefined);
    });

    expect(result.current.settings.guidedPlanningDraft).toBeUndefined();
  });
});

describe('useSettings', () => {
  it('throws error when used outside SettingsProvider', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      renderHook(() => useSettings());
    }).toThrow('useSettings must be used within a SettingsProvider');

    consoleSpy.mockRestore();
  });

  it('works correctly within SettingsProvider', () => {
    const { result } = renderHook(() => useSettings(), {
      wrapper: SettingsProvider,
    });

    expect(result.current.settings).toBeDefined();
    expect(result.current.updateSetting).toBeDefined();
    expect(typeof result.current.updateSetting).toBe('function');
  });
});

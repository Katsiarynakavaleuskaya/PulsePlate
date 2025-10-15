import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, renderHook, act, cleanup } from '@testing-library/react';
import { SettingsProvider, useSettings } from '../settings';

describe('SettingsProvider', () => {
  afterEach(() => {
    cleanup();
  });

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

  it('allows updating settings', () => {
    const { result } = renderHook(() => useSettings(), {
      wrapper: SettingsProvider,
    });

    act(() => {
      result.current.updateSetting('theme', 'dark');
    });

    expect(result.current.settings).toEqual({ theme: 'dark' });
  });

  it('allows updating multiple settings', () => {
    const { result } = renderHook(() => useSettings(), {
      wrapper: SettingsProvider,
    });

    act(() => {
      result.current.updateSetting('theme', 'dark');
      result.current.updateSetting('language', 'en');
    });

    expect(result.current.settings).toEqual({
      theme: 'dark',
      language: 'en'
    });
  });

  it('overwrites existing settings', () => {
    const { result } = renderHook(() => useSettings(), {
      wrapper: SettingsProvider,
    });

    act(() => {
      result.current.updateSetting('theme', 'light');
      result.current.updateSetting('theme', 'dark');
    });

    expect(result.current.settings).toEqual({ theme: 'dark' });
  });

  it('handles complex setting values', () => {
    const { result } = renderHook(() => useSettings(), {
      wrapper: SettingsProvider,
    });

    const complexValue = {
      colors: ['red', 'blue'],
      config: { enabled: true }
    };

    act(() => {
      result.current.updateSetting('complex', complexValue);
    });

    expect(result.current.settings).toEqual({ complex: complexValue });
  });
});

describe('useSettings', () => {
  it('throws error when used outside SettingsProvider', () => {
    // Suppress console.error for this test
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

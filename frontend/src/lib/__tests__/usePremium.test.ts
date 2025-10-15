import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePremium } from '../usePremium';

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('usePremium', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(null);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns false when localStorage is empty', () => {
    localStorageMock.getItem.mockReturnValue(null);

    const { result } = renderHook(() => usePremium());

    // After useEffect runs, it should be false (empty localStorage)
    expect(result.current).toBe(false);
  });


  it('returns true when localStorage has premium value as "true"', () => {
    localStorageMock.getItem.mockReturnValue('true');

    const { result } = renderHook(() => usePremium());

    expect(result.current).toBe(true);
  });

  it('returns false when localStorage has premium value as "false"', () => {
    localStorageMock.getItem.mockReturnValue('false');

    const { result } = renderHook(() => usePremium());

    expect(result.current).toBe(false);
  });

  it('handles localStorage errors gracefully', () => {
    localStorageMock.getItem.mockImplementation(() => {
      throw new Error('localStorage error');
    });

    const { result } = renderHook(() => usePremium());

    expect(result.current).toBe(false);
  });

  it('listens to storage events', () => {
    const { result } = renderHook(() => usePremium());

    // Initial state
    expect(result.current).toBe(false);

    // Simulate storage event
    act(() => {
      const storageEvent = new StorageEvent('storage', {
        key: 'pp_premium',
        newValue: 'true',
        oldValue: 'false',
      });
      window.dispatchEvent(storageEvent);
    });

    expect(result.current).toBe(true);
  });

  it('ignores storage events for other keys', () => {
    const { result } = renderHook(() => usePremium());

    // Initial state
    expect(result.current).toBe(false);

    // Simulate storage event for different key
    act(() => {
      const storageEvent = new StorageEvent('storage', {
        key: 'other_key',
        newValue: 'true',
        oldValue: 'false',
      });
      window.dispatchEvent(storageEvent);
    });

    expect(result.current).toBe(false);
  });

  it('listens to custom pp-premium-change events', () => {
    localStorageMock.getItem.mockReturnValue('false');
    const { result } = renderHook(() => usePremium());

    // Initial state
    expect(result.current).toBe(false);

    // Change localStorage value
    localStorageMock.getItem.mockReturnValue('true');

    // Simulate custom event
    act(() => {
      const customEvent = new Event('pp-premium-change');
      window.dispatchEvent(customEvent);
    });

    expect(result.current).toBe(true);
  });

  it('cleans up event listeners on unmount', () => {
    const removeEventListenerSpy = vi.spyOn(window, 'removeEventListener');
    const { unmount } = renderHook(() => usePremium());

    unmount();

    expect(removeEventListenerSpy).toHaveBeenCalledWith('storage', expect.any(Function));
    expect(removeEventListenerSpy).toHaveBeenCalledWith('pp-premium-change', expect.any(Function));
  });
});

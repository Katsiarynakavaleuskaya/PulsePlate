import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useApiKey } from '../useApiKey';
import { useAuth } from '../auth';

// Mock useAuth
vi.mock('../auth', () => ({
  useAuth: vi.fn(),
}));

describe('useApiKey', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  it('returns API key management functions from useAuth', () => {
    const mockApiKey = 'test-api-key';
    const mockSetApiKey = vi.fn();
    const mockClearApiKey = vi.fn();
    const mockIsAuthenticated = true;

    (useAuth as any).mockReturnValue({
      apiKey: mockApiKey,
      setApiKey: mockSetApiKey,
      clearApiKey: mockClearApiKey,
      isAuthenticated: mockIsAuthenticated,
    });

    const { result } = renderHook(() => useApiKey());

    expect(result.current.apiKey).toBe(mockApiKey);
    expect(result.current.setApiKey).toBe(mockSetApiKey);
    expect(result.current.clearApiKey).toBe(mockClearApiKey);
    expect(result.current.isAuthenticated).toBe(mockIsAuthenticated);
  });

  it('returns undefined values when useAuth returns undefined', () => {
    (useAuth as any).mockReturnValue({
      apiKey: undefined,
      setApiKey: undefined,
      clearApiKey: undefined,
      isAuthenticated: false,
    });

    const { result } = renderHook(() => useApiKey());

    expect(result.current.apiKey).toBeUndefined();
    expect(result.current.setApiKey).toBeUndefined();
    expect(result.current.clearApiKey).toBeUndefined();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('calls useAuth hook', () => {
    (useAuth as any).mockReturnValue({
      apiKey: 'test',
      setApiKey: vi.fn(),
      clearApiKey: vi.fn(),
      isAuthenticated: true,
    });

    renderHook(() => useApiKey());

    expect(useAuth).toHaveBeenCalledTimes(1);
  });
});

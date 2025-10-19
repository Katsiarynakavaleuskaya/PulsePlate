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

    vi.mocked(useAuth).mockReturnValue({
      apiKey: mockApiKey,
      setApiKey: mockSetApiKey,
      clearApiKey: mockClearApiKey,
      isAuthenticated: mockIsAuthenticated,
      isLoading: false,
      showAuthPrompt: false,
      setShowAuthPrompt: vi.fn(),
    });

    const { result } = renderHook(() => useApiKey());

    expect(result.current.apiKey).toBe(mockApiKey);
    expect(result.current.setApiKey).toBe(mockSetApiKey);
    expect(result.current.clearApiKey).toBe(mockClearApiKey);
    expect(result.current.isAuthenticated).toBe(mockIsAuthenticated);
  });

  it('returns undefined values when useAuth returns undefined', () => {
    vi.mocked(useAuth).mockReturnValue({
      apiKey: null,
      setApiKey: vi.fn(),
      clearApiKey: vi.fn(),
      isAuthenticated: false,
      isLoading: false,
      showAuthPrompt: false,
      setShowAuthPrompt: vi.fn(),
    });

    const { result } = renderHook(() => useApiKey());

    expect(result.current.apiKey).toBeNull();
    expect(result.current.setApiKey).toBeDefined();
    expect(result.current.clearApiKey).toBeDefined();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('calls useAuth hook', () => {
    vi.mocked(useAuth).mockReturnValue({
      apiKey: 'test',
      setApiKey: vi.fn(),
      clearApiKey: vi.fn(),
      isAuthenticated: true,
      isLoading: false,
      showAuthPrompt: false,
      setShowAuthPrompt: vi.fn(),
    });

    renderHook(() => useApiKey());

    expect(useAuth).toHaveBeenCalledTimes(1);
  });
});

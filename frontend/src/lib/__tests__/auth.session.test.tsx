// @vitest-environment jsdom
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '../auth';

const checkProSessionMock = vi.fn<() => Promise<boolean>>();
const exchangeApiKeyForSessionMock = vi.fn<(apiKey: string) => Promise<boolean>>();
const clearProSessionMock = vi.fn<() => Promise<void>>();
const getStoredApiKeyMock = vi.fn<() => string | null>();
const clearStoredApiKeyMock = vi.fn<() => void>();
let legacyStoredKey: string | null = null;

vi.mock('../../api/client', () => ({
  checkProSession: (...args: []) => checkProSessionMock(...args),
  exchangeApiKeyForSession: (apiKey: string) => exchangeApiKeyForSessionMock(apiKey),
  clearProSession: (...args: []) => clearProSessionMock(...args),
}));

vi.mock('../../auth/storage', () => ({
  getStoredApiKey: (...args: []) => getStoredApiKeyMock(...args),
  clearStoredApiKey: (...args: []) => clearStoredApiKeyMock(...args),
}));

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
);

describe('AuthProvider session migration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    legacyStoredKey = null;
    getStoredApiKeyMock.mockImplementation(() => legacyStoredKey);
    clearStoredApiKeyMock.mockImplementation(() => {
      legacyStoredKey = null;
    });
    checkProSessionMock.mockResolvedValue(false);
    exchangeApiKeyForSessionMock.mockResolvedValue(true);
    clearProSessionMock.mockResolvedValue(undefined);
  });

  it('migrates legacy stored API key to session and clears storage', async () => {
    legacyStoredKey = 'legacy-session-key';
    checkProSessionMock.mockResolvedValue(true);

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(exchangeApiKeyForSessionMock).toHaveBeenCalledWith('legacy-session-key');
    expect(clearStoredApiKeyMock).toHaveBeenCalled();
    expect(legacyStoredKey).toBeNull();
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.apiKey).not.toBeNull();
  });

  it('setApiKey exchanges for session and never persists key in storage', async () => {
    checkProSessionMock.mockResolvedValueOnce(false).mockResolvedValueOnce(true);

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.setApiKey('sk-session12345678901234567890');
    });

    expect(exchangeApiKeyForSessionMock).toHaveBeenCalledWith('sk-session12345678901234567890');
    expect(clearStoredApiKeyMock).toHaveBeenCalled();
    expect(legacyStoredKey).toBeNull();
    expect(result.current.isAuthenticated).toBe(true);
  });
});

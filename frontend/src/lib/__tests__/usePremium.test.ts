import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { usePremium } from '../usePremium';
import { getProSessionStatus } from '../../api/client';

vi.mock('../../api/client', () => ({
  getProSessionStatus: vi.fn(),
}));

describe('usePremium', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getProSessionStatus).mockResolvedValue(null);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns false when no server session is available', async () => {
    const { result } = renderHook(() => usePremium());
    await waitFor(() => {
      expect(result.current).toBe(false);
    });
  });

  it('returns true for PRO session payloads', async () => {
    vi.mocked(getProSessionStatus).mockResolvedValue({
      status: 'ok',
      authenticated: true,
      auth_source: 'cookie',
      tier: 'PRO',
    });
    const { result } = renderHook(() => usePremium());
    await waitFor(() => {
      expect(result.current).toBe(true);
    });
  });

  it('returns true for VIP session payloads', async () => {
    vi.mocked(getProSessionStatus).mockResolvedValue({
      status: 'ok',
      authenticated: true,
      auth_source: 'header',
      tier: 'VIP',
    });
    const { result } = renderHook(() => usePremium());
    await waitFor(() => {
      expect(result.current).toBe(true);
    });
  });

  it('fails closed when session lookup rejects', async () => {
    vi.mocked(getProSessionStatus).mockRejectedValue(new Error('session unavailable'));
    const { result } = renderHook(() => usePremium());
    await waitFor(() => {
      expect(result.current).toBe(false);
    });
  });

  it('does not set state after unmount', async () => {
    let resolveSession: ((value: Awaited<ReturnType<typeof getProSessionStatus>>) => void) | null = null;
    vi.mocked(getProSessionStatus).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveSession = resolve;
        })
    );
    const { unmount } = renderHook(() => usePremium());
    unmount();
    resolveSession?.({
      status: 'ok',
      authenticated: true,
      auth_source: 'cookie',
      tier: 'PRO',
    });
    await Promise.resolve();
    expect(getProSessionStatus).toHaveBeenCalledTimes(1);
  });
});

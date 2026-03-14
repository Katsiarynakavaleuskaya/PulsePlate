import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { usePremium } from '../usePremium';
import { getProSessionStatus } from '../../api/client';
import { PREMIUM_CHANGE_EVENT } from '../premiumEvents';

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
    let release!: () => void;
    vi.mocked(getProSessionStatus).mockImplementation(
      () =>
        new Promise((resolve) => {
          release = () =>
            resolve({
              status: 'ok',
              authenticated: true,
              auth_source: 'cookie',
              tier: 'PRO',
            });
        })
    );
    const { unmount } = renderHook(() => usePremium());
    unmount();
    release();
    await Promise.resolve();
    expect(getProSessionStatus).toHaveBeenCalledTimes(1);
  });

  it('revalidates premium state after a same-document session change event', async () => {
    vi.mocked(getProSessionStatus)
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce({
        status: 'ok',
        authenticated: true,
        auth_source: 'cookie',
        tier: 'PRO',
      });

    const { result } = renderHook(() => usePremium());

    await waitFor(() => {
      expect(result.current).toBe(false);
    });

    await act(async () => {
      window.dispatchEvent(new Event(PREMIUM_CHANGE_EVENT));
    });

    await waitFor(() => {
      expect(result.current).toBe(true);
    });

    expect(getProSessionStatus).toHaveBeenCalledTimes(2);
  });
});

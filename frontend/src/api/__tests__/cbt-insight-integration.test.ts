import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getCbtInsight } from '../premium/cbt-insight';

vi.mock('../client', async () => {
  const actual = await vi.importActual<typeof import('../client')>('../client');
  return {
    ...actual,
    api: vi.fn(),
  };
});

import { api } from '../client';

describe('CBT Insight API integration', () => {
  const mockApi = vi.mocked(api);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls api() with canonical endpoint and JSON enforcement', async () => {
    const response = {
      insight: 'Server-authored guidance',
      confidence: 0.91,
      uncertainty: 0.09,
      rag_used: true,
      sources: [],
      warnings: [],
      mode: 'auto-safe' as const,
      quota_state: 'consumed' as const,
    };
    mockApi.mockResolvedValue(response);

    const body = { query: 'What should I focus on this week?' };
    const result = await getCbtInsight(body);

    expect(result).toEqual(response);
    expect(mockApi).toHaveBeenCalledWith(
      '/api/v1/pro/cbt/insight',
      expect.objectContaining({
        method: 'POST',
        body,
        signal: undefined,
      }),
      undefined,
      true
    );
  });

  it('forwards signal and onAuthError through PremiumRequestOptions', async () => {
    const onAuthError = vi.fn();
    const signal = new AbortController().signal;
    mockApi.mockResolvedValue({
      insight: 'Fallback guidance',
      confidence: 0.5,
      uncertainty: 0.5,
      rag_used: false,
      sources: [],
      warnings: ['fallback'],
      mode: 'review-required' as const,
      quota_state: 'not_consumed' as const,
    });

    await getCbtInsight({ query: 'Check auth propagation' }, { signal, onAuthError });

    expect(mockApi).toHaveBeenCalledWith(
      '/api/v1/pro/cbt/insight',
      expect.objectContaining({
        method: 'POST',
        body: { query: 'Check auth propagation' },
        signal,
      }),
      { onAuthError },
      true
    );
  });
});

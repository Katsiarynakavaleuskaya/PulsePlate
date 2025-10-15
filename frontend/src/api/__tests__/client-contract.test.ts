/** @vitest-environment jsdom */
import { describe, it, expect, vi } from 'vitest';
import { setApiClientDependencies, api, UnauthorizedError } from '../client';
import type { components } from '../schema';

describe('API Client – Contract (OpenAPI types)', () => {
  const apiBase = 'http://localhost:8000/api/v1';

  beforeEach(() => {
    setApiClientDependencies({
      apiBase,
      getStoredApiKey: () => 'test-key',
      clearStoredApiKey: vi.fn(),
    });
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    setApiClientDependencies(null);
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('returns data matching WeekPlanResponse type on success', async () => {
    const mockBody: components['schemas']['WeekPlanResponse'] = {
      daily_menus: [{}],
      weekly_coverage: { protein: 1 },
      shopping_list: { milk: 2 },
      total_cost: 12.34,
      adherence_score: 0.9,
    };

    (fetch as unknown as vi.Mock).mockResolvedValueOnce(
      new Response(JSON.stringify(mockBody), { status: 200, headers: { 'Content-Type': 'application/json' } })
    );

    const data = await api<components['schemas']['WeekPlanResponse']>('/premium/plan/week', { method: 'POST', body: {} });
    expect(data.total_cost).toBeCloseTo(12.34);
    expect(Object.keys(data.weekly_coverage).length).toBeGreaterThan(0);
  });

  it('throws UnauthorizedError on 401 with typed response path', async () => {
    (fetch as unknown as vi.Mock).mockResolvedValueOnce(new Response('unauthorized', { status: 401 }));

    await expect(
      api<components['schemas']['WeekPlanResponse']>('/premium/plan/week', { method: 'POST', body: {} })
    ).rejects.toBeInstanceOf(UnauthorizedError);
  });
});

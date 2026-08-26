import { beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest';
import type { FitChefSupportHandoffResponse } from '../fitchefSupportHandoff';

const apiMock = vi.hoisted(() => vi.fn());

vi.mock('../client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../client')>();
  return {
    ...actual,
    api: apiMock,
  };
});

import { ApiHttpError, UnauthorizedError } from '../client';
import {
  FITCHEF_SUPPORT_HANDOFF_PATH,
  FitChefSupportHandoffValidationError,
  parseFitChefSupportHandoffResponse,
  requestFitChefSupportHandoff,
  type FitChefSupportHandoffRequest,
  type FitChefSupportNeed,
} from '../fitchefSupportHandoff';

function validPayload(
  supportNeed: FitChefSupportNeed = 'daily_structure'
): FitChefSupportHandoffResponse {
  if (supportNeed === 'daily_structure') {
    return {
      schema_version: 'fitchef_support_handoff.v1',
      scenario: 'support_handoff',
      support_need: 'daily_structure',
      action: {
        action_type: 'handoff_to_product_surface',
        target_surface: 'pro_daily_plate',
      },
      user_confirmation_required: true,
      execution_authority: false,
      plan_mutation_authority: false,
      used_llm: false,
      wellness_boundary: 'wellness_planning_only',
    };
  }

  return {
    schema_version: 'fitchef_support_handoff.v1',
    scenario: 'support_handoff',
    support_need: 'weekly_structure',
    action: {
      action_type: 'handoff_to_product_surface',
      target_surface: 'pro_weekly_plan',
    },
    user_confirmation_required: true,
    execution_authority: false,
    plan_mutation_authority: false,
    used_llm: false,
    wellness_boundary: 'wellness_planning_only',
  };
}

describe('FitChef support handoff adapter', () => {
  beforeEach(() => {
    apiMock.mockReset();
  });

  it('derives the request and response surface from generated OpenAPI types', () => {
    expectTypeOf<FitChefSupportHandoffRequest>().toEqualTypeOf<{
      support_need: 'daily_structure' | 'weekly_structure';
    }>();
    expectTypeOf<FitChefSupportHandoffResponse['support_need']>().toEqualTypeOf<
      'daily_structure' | 'weekly_structure'
    >();
  });

  it.each([
    ['daily_structure', 'pro_daily_plate'],
    ['weekly_structure', 'pro_weekly_plan'],
  ] as const)(
    'posts the exact %s request once and validates the %s response',
    async (supportNeed, targetSurface) => {
      const payload = validPayload(supportNeed);
      const controller = new AbortController();
      const onAuthError = vi.fn();
      apiMock.mockResolvedValueOnce(payload);

      const result = await requestFitChefSupportHandoff(supportNeed, {
        signal: controller.signal,
        onAuthError,
      });

      expect(result).toEqual(payload);
      expect(result).not.toBe(payload);
      expect(result.action).not.toBe(payload.action);
      expect(result.action.target_surface).toBe(targetSurface);
      expect(apiMock).toHaveBeenCalledTimes(1);
      expect(apiMock).toHaveBeenCalledWith(
        FITCHEF_SUPPORT_HANDOFF_PATH,
        {
          method: 'POST',
          body: { support_need: supportNeed },
          signal: controller.signal,
        },
        { onAuthError, structuredHttpErrors: true }
      );
      expect(apiMock.mock.calls[0]?.[1]).not.toHaveProperty('forceMock');
    }
  );

  it('always supplies a no-redirect auth callback when the caller omits one', async () => {
    apiMock.mockResolvedValueOnce(validPayload());

    await requestFitChefSupportHandoff('daily_structure');

    const options = apiMock.mock.calls[0]?.[2] as {
      onAuthError?: (status: 401 | 403, helpers: { clearApiKey: () => void }) => void;
      structuredHttpErrors?: boolean;
    };
    expect(options.onAuthError).toEqual(expect.any(Function));
    expect(options.structuredHttpErrors).toBe(true);
    expect(() => options.onAuthError?.(401, { clearApiKey: vi.fn() })).not.toThrow();
  });

  it.each([
    ['null', null],
    ['array', []],
    ['string', 'support_handoff'],
    [
      'missing field',
      (() => {
        const { used_llm: _unused, ...payload } = validPayload();
        return payload;
      })(),
    ],
    ['unknown top-level field', { ...validPayload(), extra: 'not-authorized' }],
    [
      'unknown action field',
      { ...validPayload(), action: { ...validPayload().action, href: '/plate' } },
    ],
    [
      'cross pair daily to weekly',
      {
        ...validPayload('daily_structure'),
        action: {
          action_type: 'handoff_to_product_surface',
          target_surface: 'pro_weekly_plan',
        },
      },
    ],
    [
      'cross pair weekly to daily',
      {
        ...validPayload('weekly_structure'),
        action: {
          action_type: 'handoff_to_product_surface',
          target_surface: 'pro_daily_plate',
        },
      },
    ],
    ['unknown need', { ...validPayload(), support_need: 'inferred_need' }],
    [
      'unknown target',
      { ...validPayload(), action: { ...validPayload().action, target_surface: '/plate' } },
    ],
    ['wrong schema', { ...validPayload(), schema_version: 'fitchef_support_handoff.v2' }],
    ['wrong scenario', { ...validPayload(), scenario: 'recommendation' }],
    [
      'wrong action',
      { ...validPayload(), action: { ...validPayload().action, action_type: 'navigate' } },
    ],
    ['coercive confirmation', { ...validPayload(), user_confirmation_required: 1 }],
    ['execution authority', { ...validPayload(), execution_authority: true }],
    ['plan mutation authority', { ...validPayload(), plan_mutation_authority: true }],
    ['LLM authority', { ...validPayload(), used_llm: true }],
    ['wrong wellness boundary', { ...validPayload(), wellness_boundary: 'general' }],
  ])('rejects %s without repairing the descriptor', (_label, candidate) => {
    expect(() => parseFitChefSupportHandoffResponse(candidate)).toThrow(
      FitChefSupportHandoffValidationError
    );
  });

  it('rejects an enumerable symbol key in the exact own-key set', () => {
    const candidate = validPayload() as FitChefSupportHandoffResponse & {
      [key: symbol]: string;
    };
    Object.defineProperty(candidate, Symbol('extra'), {
      enumerable: true,
      value: 'not-authorized',
    });

    expect(() => parseFitChefSupportHandoffResponse(candidate)).toThrow(
      FitChefSupportHandoffValidationError
    );
  });

  it.each(['top-level', 'action'] as const)(
    'rejects a %s object with a non-plain prototype',
    (location) => {
      const payload = validPayload();
      const candidate =
        location === 'top-level'
          ? Object.assign(Object.create({ inherited: true }), payload)
          : {
              ...payload,
              action: Object.assign(Object.create({ inherited: true }), payload.action),
            };

      expect(() => parseFitChefSupportHandoffResponse(candidate)).toThrow(
        FitChefSupportHandoffValidationError
      );
    }
  );

  it('accepts exact JSON-shaped records with a null prototype', () => {
    const payload = validPayload();
    const candidate = Object.assign(Object.create(null), payload) as Record<string, unknown>;
    candidate.action = Object.assign(Object.create(null), payload.action);

    expect(parseFitChefSupportHandoffResponse(candidate)).toEqual(payload);
  });

  it('rejects a valid descriptor that does not echo the submitted need', async () => {
    apiMock.mockResolvedValueOnce(validPayload('weekly_structure'));

    await expect(requestFitChefSupportHandoff('daily_structure')).rejects.toThrow(
      FitChefSupportHandoffValidationError
    );
  });

  it('maps malformed response JSON to the stable validation error', async () => {
    apiMock.mockRejectedValueOnce(new SyntaxError('raw response parse detail'));

    await expect(requestFitChefSupportHandoff('daily_structure')).rejects.toThrow(
      FitChefSupportHandoffValidationError
    );
  });

  it.each([401, 403] as const)(
    'preserves UnauthorizedError and forwards the inline auth callback for HTTP %s',
    async (status) => {
      const onAuthError = vi.fn();
      apiMock.mockImplementationOnce(
        async (
          _path: string,
          _init: RequestInit,
          options: {
            onAuthError: (code: 401 | 403, helpers: { clearApiKey: () => void }) => void;
          }
        ) => {
          options.onAuthError(status, { clearApiKey: vi.fn() });
          throw new UnauthorizedError(`auth ${status}`);
        }
      );

      await expect(
        requestFitChefSupportHandoff('daily_structure', { onAuthError })
      ).rejects.toThrow(UnauthorizedError);
      expect(onAuthError).toHaveBeenCalledWith(status, {
        clearApiKey: expect.any(Function),
      });
    }
  );

  it.each([422, 503, 500])('preserves structured HTTP %s failures', async (status) => {
    apiMock.mockRejectedValueOnce(new ApiHttpError(status));

    const error = await requestFitChefSupportHandoff('daily_structure').catch(
      (caught: unknown) => caught
    );

    expect(error).toBeInstanceOf(ApiHttpError);
    expect(error).toMatchObject({ status });
  });

  it('preserves network failures without fallback success', async () => {
    const networkError = new TypeError('offline');
    apiMock.mockRejectedValueOnce(networkError);

    await expect(requestFitChefSupportHandoff('daily_structure')).rejects.toBe(networkError);
    expect(apiMock).toHaveBeenCalledTimes(1);
  });

  it('preserves AbortError without retrying', async () => {
    const abortError = new DOMException('aborted', 'AbortError');
    apiMock.mockRejectedValueOnce(abortError);

    await expect(requestFitChefSupportHandoff('weekly_structure')).rejects.toBe(abortError);
    expect(apiMock).toHaveBeenCalledTimes(1);
  });
});

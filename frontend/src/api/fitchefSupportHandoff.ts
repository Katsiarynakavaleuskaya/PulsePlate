import { api, type ApiOptions } from './client';
import type { components, operations } from './schema';

export const FITCHEF_SUPPORT_HANDOFF_PATH = '/api/v1/pro/fitchef/recommend' as const;

type FitChefSupportHandoffOperation =
  operations['fitchef_support_handoff_api_v1_pro_fitchef_recommend_post'];

export type FitChefSupportHandoffRequest =
  FitChefSupportHandoffOperation['requestBody']['content']['application/json'];
export type FitChefSupportNeed = FitChefSupportHandoffRequest['support_need'];
export type FitChefSupportHandoffResponse = components['schemas']['FitChefSupportHandoffResponse'];
export type FitChefSupportTargetSurface = FitChefSupportHandoffResponse['action']['target_surface'];

export interface FitChefSupportHandoffRequestOptions {
  signal?: AbortSignal;
  onAuthError?: ApiOptions['onAuthError'];
}

export class FitChefSupportHandoffValidationError extends Error {
  constructor() {
    super('FitChef support handoff response failed validation.');
    this.name = 'FitChefSupportHandoffValidationError';
  }
}

const TOP_LEVEL_KEYS = [
  'schema_version',
  'scenario',
  'support_need',
  'action',
  'user_confirmation_required',
  'execution_authority',
  'plan_mutation_authority',
  'used_llm',
  'wellness_boundary',
] as const;

const ACTION_KEYS = ['action_type', 'target_surface'] as const;

function hasExactOwnEnumerableKeys(
  value: unknown,
  expectedKeys: readonly string[]
): value is Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    return false;
  }

  const prototype = Object.getPrototypeOf(value);
  if (prototype !== Object.prototype && prototype !== null) {
    return false;
  }

  const enumerableKeys = Reflect.ownKeys(value).filter((key) =>
    Object.prototype.propertyIsEnumerable.call(value, key)
  );

  return (
    enumerableKeys.length === expectedKeys.length &&
    expectedKeys.every((key) => enumerableKeys.includes(key))
  );
}

function isFitChefSupportNeed(value: unknown): value is FitChefSupportNeed {
  return value === 'daily_structure' || value === 'weekly_structure';
}

function isFitChefSupportTargetSurface(value: unknown): value is FitChefSupportTargetSurface {
  return value === 'pro_daily_plate' || value === 'pro_weekly_plan';
}

function isValidNeedSurfacePair(
  supportNeed: FitChefSupportNeed,
  targetSurface: FitChefSupportTargetSurface
): boolean {
  return (
    (supportNeed === 'daily_structure' && targetSurface === 'pro_daily_plate') ||
    (supportNeed === 'weekly_structure' && targetSurface === 'pro_weekly_plan')
  );
}

/**
 * Validate the complete frozen descriptor returned by response.json().
 *
 * The result is a fresh projection. Unknown response fields, incompatible
 * need/surface pairs, and coercive values fail closed; no target is inferred
 * or repaired from request context.
 */
export function parseFitChefSupportHandoffResponse(value: unknown): FitChefSupportHandoffResponse {
  if (!hasExactOwnEnumerableKeys(value, TOP_LEVEL_KEYS)) {
    throw new FitChefSupportHandoffValidationError();
  }

  const action = value.action;
  if (!hasExactOwnEnumerableKeys(action, ACTION_KEYS)) {
    throw new FitChefSupportHandoffValidationError();
  }

  if (
    value.schema_version !== 'fitchef_support_handoff.v1' ||
    value.scenario !== 'support_handoff' ||
    action.action_type !== 'handoff_to_product_surface' ||
    !isFitChefSupportNeed(value.support_need) ||
    !isFitChefSupportTargetSurface(action.target_surface) ||
    !isValidNeedSurfacePair(value.support_need, action.target_surface) ||
    value.user_confirmation_required !== true ||
    value.execution_authority !== false ||
    value.plan_mutation_authority !== false ||
    value.used_llm !== false ||
    value.wellness_boundary !== 'wellness_planning_only'
  ) {
    throw new FitChefSupportHandoffValidationError();
  }

  if (value.support_need === 'daily_structure' && action.target_surface === 'pro_daily_plate') {
    return {
      schema_version: 'fitchef_support_handoff.v1',
      scenario: 'support_handoff',
      support_need: value.support_need,
      action: {
        action_type: 'handoff_to_product_surface',
        target_surface: action.target_surface,
      },
      user_confirmation_required: true,
      execution_authority: false,
      plan_mutation_authority: false,
      used_llm: false,
      wellness_boundary: 'wellness_planning_only',
    };
  }

  // The closed pair validation above plus the non-daily branch proves the
  // weekly pair. Return a fresh literal projection; never copy or repair an
  // unvalidated target from request context.
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

/**
 * Request one backend-owned, non-executing FitChef product-area pointer.
 */
export async function requestFitChefSupportHandoff(
  supportNeed: FitChefSupportNeed,
  options: FitChefSupportHandoffRequestOptions = {}
): Promise<FitChefSupportHandoffResponse> {
  const requestBody: FitChefSupportHandoffRequest = { support_need: supportNeed };
  let payload: unknown;

  try {
    payload = await api<unknown>(
      FITCHEF_SUPPORT_HANDOFF_PATH,
      {
        method: 'POST',
        body: requestBody,
        signal: options.signal,
      },
      {
        // Supplying a callback keeps this bounded consumer inline and prevents
        // the shared client's legacy redirect fallback.
        onAuthError: options.onAuthError ?? (() => undefined),
        structuredHttpErrors: true,
      }
    );
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new FitChefSupportHandoffValidationError();
    }
    throw error;
  }

  const response = parseFitChefSupportHandoffResponse(payload);
  if (response.support_need !== supportNeed) {
    throw new FitChefSupportHandoffValidationError();
  }
  return response;
}

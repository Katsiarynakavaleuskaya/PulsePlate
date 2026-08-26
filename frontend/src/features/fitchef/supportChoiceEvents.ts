import type {
  FitChefSupportNeed,
  FitChefSupportTargetSurface,
} from '../../api/fitchefSupportHandoff';

export const fitChefSupportChoiceEventNames = [
  'fitchef_support_choice_viewed',
  'fitchef_support_need_selected',
  'fitchef_support_handoff_received',
  'fitchef_support_handoff_confirmed',
  'fitchef_support_handoff_exited',
] as const;

export type FitChefSupportChoiceEventName = (typeof fitChefSupportChoiceEventNames)[number];
export type FitChefSupportAuthState = 'authenticated' | 'unauthenticated' | 'unknown';
export type FitChefSupportExitOutcome =
  | 'dismissed'
  | 'changed_selection'
  | 'network_error'
  | 'auth_error'
  | 'feature_unavailable'
  | 'validation_error';

interface FitChefSupportChoiceEventBase {
  surface: 'app';
  componentId: 'fitchef-support-choice';
  routePath: '/app';
}

export type FitChefSupportChoiceEvent =
  | {
      name: 'fitchef_support_choice_viewed';
      payload: FitChefSupportChoiceEventBase;
    }
  | {
      name: 'fitchef_support_need_selected';
      payload: FitChefSupportChoiceEventBase & {
        supportNeed: FitChefSupportNeed;
        authState: 'authenticated';
      };
    }
  | {
      name: 'fitchef_support_handoff_received' | 'fitchef_support_handoff_confirmed';
      payload: FitChefSupportChoiceEventBase & {
        supportNeed: FitChefSupportNeed;
        targetSurface: FitChefSupportTargetSurface;
        authState: 'authenticated';
      };
    }
  | {
      name: 'fitchef_support_handoff_exited';
      payload: FitChefSupportChoiceEventBase & {
        outcome: FitChefSupportExitOutcome;
        supportNeed?: FitChefSupportNeed;
        targetSurface?: FitChefSupportTargetSurface;
      };
    };

type FitChefSupportChoiceEventSink = (event: FitChefSupportChoiceEvent) => void;

const BASE_KEYS = ['surface', 'componentId', 'routePath'] as const;
const SELECTED_KEYS = [...BASE_KEYS, 'supportNeed', 'authState'] as const;
const RECEIVED_KEYS = [...BASE_KEYS, 'supportNeed', 'targetSurface', 'authState'] as const;
const EXIT_KEYS = [...BASE_KEYS, 'outcome'] as const;
const EXIT_NEED_KEYS = [...EXIT_KEYS, 'supportNeed'] as const;
const EXIT_RESULT_KEYS = [...EXIT_NEED_KEYS, 'targetSurface'] as const;

let fitChefSupportChoiceEventSink: FitChefSupportChoiceEventSink | null = null;

export const fitChefSupportChoiceSensitiveFields = [
  'freeText',
  'rawError',
  'goal',
  'plan',
  'planContents',
  'nutritionTargets',
  'weight',
  'bmi',
  'email',
  'name',
  'sessionToken',
  'apiKey',
  'timestamp',
  'cookieId',
  'trackingId',
  'deviceId',
] as const;

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

function isBasePayload(payload: Record<string, unknown>): boolean {
  return (
    payload.surface === 'app' &&
    payload.componentId === 'fitchef-support-choice' &&
    payload.routePath === '/app'
  );
}

function isSupportNeed(value: unknown): value is FitChefSupportNeed {
  return value === 'daily_structure' || value === 'weekly_structure';
}

function isTargetSurface(value: unknown): value is FitChefSupportTargetSurface {
  return value === 'pro_daily_plate' || value === 'pro_weekly_plan';
}

function isAuthenticatedEventState(value: unknown): value is 'authenticated' {
  return value === 'authenticated';
}

function isExitOutcome(value: unknown): value is FitChefSupportExitOutcome {
  return (
    value === 'dismissed' ||
    value === 'changed_selection' ||
    value === 'network_error' ||
    value === 'auth_error' ||
    value === 'feature_unavailable' ||
    value === 'validation_error'
  );
}

function isCompatiblePair(
  supportNeed: FitChefSupportNeed,
  targetSurface: FitChefSupportTargetSurface
): boolean {
  return (
    (supportNeed === 'daily_structure' && targetSurface === 'pro_daily_plate') ||
    (supportNeed === 'weekly_structure' && targetSurface === 'pro_weekly_plan')
  );
}

function recognizeFitChefSupportChoiceEvent(candidate: unknown): FitChefSupportChoiceEvent | null {
  if (!hasExactOwnEnumerableKeys(candidate, ['name', 'payload'])) {
    return null;
  }

  const { name, payload } = candidate;
  if (typeof name !== 'string' || payload === null || typeof payload !== 'object') {
    return null;
  }

  if (name === 'fitchef_support_choice_viewed') {
    if (!hasExactOwnEnumerableKeys(payload, BASE_KEYS) || !isBasePayload(payload)) {
      return null;
    }
    return {
      name,
      payload: {
        surface: 'app',
        componentId: 'fitchef-support-choice',
        routePath: '/app',
      },
    };
  }

  if (name === 'fitchef_support_need_selected') {
    if (
      !hasExactOwnEnumerableKeys(payload, SELECTED_KEYS) ||
      !isBasePayload(payload) ||
      !isSupportNeed(payload.supportNeed) ||
      !isAuthenticatedEventState(payload.authState)
    ) {
      return null;
    }
    return {
      name,
      payload: {
        surface: 'app',
        componentId: 'fitchef-support-choice',
        routePath: '/app',
        supportNeed: payload.supportNeed,
        authState: payload.authState,
      },
    };
  }

  if (name === 'fitchef_support_handoff_received' || name === 'fitchef_support_handoff_confirmed') {
    if (
      !hasExactOwnEnumerableKeys(payload, RECEIVED_KEYS) ||
      !isBasePayload(payload) ||
      !isSupportNeed(payload.supportNeed) ||
      !isTargetSurface(payload.targetSurface) ||
      !isCompatiblePair(payload.supportNeed, payload.targetSurface) ||
      !isAuthenticatedEventState(payload.authState)
    ) {
      return null;
    }
    return {
      name,
      payload: {
        surface: 'app',
        componentId: 'fitchef-support-choice',
        routePath: '/app',
        supportNeed: payload.supportNeed,
        targetSurface: payload.targetSurface,
        authState: payload.authState,
      },
    };
  }

  if (name !== 'fitchef_support_handoff_exited') {
    return null;
  }

  const hasBaseExit = hasExactOwnEnumerableKeys(payload, EXIT_KEYS);
  const hasNeedExit = hasExactOwnEnumerableKeys(payload, EXIT_NEED_KEYS);
  const hasResultExit = hasExactOwnEnumerableKeys(payload, EXIT_RESULT_KEYS);
  if (
    (!hasBaseExit && !hasNeedExit && !hasResultExit) ||
    !isBasePayload(payload) ||
    !isExitOutcome(payload.outcome)
  ) {
    return null;
  }

  let supportNeed: FitChefSupportNeed | undefined;
  let targetSurface: FitChefSupportTargetSurface | undefined;
  if (hasNeedExit || hasResultExit) {
    if (!isSupportNeed(payload.supportNeed)) {
      return null;
    }
    supportNeed = payload.supportNeed;
  }
  if (hasResultExit) {
    if (
      supportNeed === undefined ||
      !isTargetSurface(payload.targetSurface) ||
      !isCompatiblePair(supportNeed, payload.targetSurface)
    ) {
      return null;
    }
    targetSurface = payload.targetSurface;
  }

  return {
    name,
    payload: {
      surface: 'app',
      componentId: 'fitchef-support-choice',
      routePath: '/app',
      outcome: payload.outcome,
      ...(supportNeed === undefined ? {} : { supportNeed }),
      ...(targetSurface === undefined ? {} : { targetSurface }),
    },
  };
}

export function setFitChefSupportChoiceEventSink(sink: FitChefSupportChoiceEventSink | null): void {
  fitChefSupportChoiceEventSink = sink;
}

/**
 * Runtime-checked local sink entrypoint used by adversarial tests and callers
 * that cross an unknown-data boundary.
 */
export function recordFitChefSupportChoiceEvent(candidate: unknown): boolean {
  const event = recognizeFitChefSupportChoiceEvent(candidate);
  if (event === null) {
    return false;
  }

  try {
    fitChefSupportChoiceEventSink?.(event);
  } catch {
    // Local observability must never break the user-facing flow.
  }
  return true;
}

export function trackFitChefSupportChoiceEvent(event: FitChefSupportChoiceEvent): void {
  recordFitChefSupportChoiceEvent(event);
}

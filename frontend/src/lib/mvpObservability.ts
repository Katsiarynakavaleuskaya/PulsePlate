export type GuidedPlanningEventName =
  | 'guided_planning_viewed'
  | 'planning_intent_selected'
  | 'planning_time_selected'
  | 'planning_preview_seen'
  | 'tier_value_viewed'
  | 'primary_planning_cta_clicked'
  | 'wellness_boundary_viewed'
  | 'planning_save_prompt_viewed'
  | 'planning_auth_prompt_viewed'
  | 'planning_progress_state_viewed'
  | 'planning_save_clicked'
  | 'planning_continue_clicked';

export type GuidedPlanningSurface = 'app';

export interface GuidedPlanningEventPayload {
  surface: GuidedPlanningSurface;
  componentId: string;
  routePath: '/app' | '/setup' | '/plate' | '/progress' | '/pro';
  optionId?: string;
  tierLabel?: 'FREE' | 'PRO' | 'VIP';
  authState?: 'authenticated' | 'unauthenticated' | 'unknown';
}

export interface GuidedPlanningEvent {
  name: GuidedPlanningEventName;
  payload: GuidedPlanningEventPayload;
}

type GuidedPlanningEventSink = (event: GuidedPlanningEvent) => void;

let guidedPlanningEventSink: GuidedPlanningEventSink | null = null;

export function setGuidedPlanningEventSink(sink: GuidedPlanningEventSink | null): void {
  guidedPlanningEventSink = sink;
}

export function trackGuidedPlanningEvent(
  name: GuidedPlanningEventName,
  payload: GuidedPlanningEventPayload
): void {
  try {
    guidedPlanningEventSink?.({ name, payload });
  } catch {
    // Observability evidence must never break the user-facing MVP flow.
  }
}

export const guidedPlanningObservabilitySensitiveFields = [
  'apiKey',
  'sessionToken',
  'sessionId',
  'email',
  'name',
  'weight',
  'height',
  'bmi',
  'healthCondition',
  'freeText',
  'nutritionTargets',
  'deviceFingerprint',
  'cookieId',
  'trackingId',
] as const;

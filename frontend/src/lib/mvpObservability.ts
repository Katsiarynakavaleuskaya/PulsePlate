export type GuidedPlanningEventName =
  | 'guided_planning_viewed'
  | 'planning_intent_selected'
  | 'planning_time_selected'
  | 'planning_preview_seen'
  | 'tier_value_viewed'
  | 'primary_planning_cta_clicked'
  | 'wellness_boundary_viewed';

export type GuidedPlanningSurface = 'app';

export interface GuidedPlanningEventPayload {
  surface: GuidedPlanningSurface;
  componentId: string;
  routePath: '/app' | '/setup' | '/plate' | '/progress' | '/pro';
  optionId?: string;
  tierLabel?: 'FREE' | 'PRO' | 'VIP';
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

export type PlanningIntentId = 'consistent' | 'balanced' | 'decision_fatigue' | 'shopping';
export type PlanningTimeId = 'quick' | 'standard' | 'batch' | 'flexible';

export interface PlanningIntent {
  id: PlanningIntentId;
  label: string;
  helper: string;
}

export interface PlanningTime {
  id: PlanningTimeId;
  label: string;
  helper: string;
}

export interface PlanningPreview {
  plateDirection: string;
  weeklyStructure: string[];
  shoppingDirection: string[];
  nextAction: string;
}

export interface GuidedPlanningDraft {
  intentId: PlanningIntentId;
  timeId: PlanningTimeId;
  savedAt?: string;
}

export const planningIntents: PlanningIntent[] = [
  {
    id: 'consistent',
    label: 'More consistent meals',
    helper: 'Build a repeatable baseline without overplanning.',
  },
  {
    id: 'balanced',
    label: 'Balanced week',
    helper: 'See how daily plates connect into a weekly rhythm.',
  },
  {
    id: 'decision_fatigue',
    label: 'Less food decision fatigue',
    helper: 'Reduce last-minute choices with simple anchors.',
  },
  {
    id: 'shopping',
    label: 'Shopping-list planning',
    helper: 'Turn meal direction into a practical grocery pass.',
  },
];

export const planningTimes: PlanningTime[] = [
  { id: 'quick', label: '10-15 min meals', helper: 'Smallest next step.' },
  { id: 'standard', label: 'Standard meal window', helper: 'Balanced prep window.' },
  { id: 'batch', label: 'Batch prep', helper: 'Repeatable anchors.' },
  { id: 'flexible', label: 'Flexible cooking', helper: 'Loose weekly plan.' },
];

export const previewByIntent: Record<PlanningIntentId, PlanningPreview> = {
  consistent: {
    plateDirection: 'Protein anchor + fiber/color side + simple grain, repeated until the routine feels easy.',
    weeklyStructure: [
      '3 repeatable breakfasts',
      '2 flexible lunches',
      '3 dinner anchors',
      '1 batch-prep slot',
    ],
    shoppingDirection: ['core proteins', 'vegetables/fruit', 'grains/pantry', 'hydration routine'],
    nextAction: 'Start with setup so PulsePlate can frame your baseline before deeper planning.',
  },
  balanced: {
    plateDirection: 'Daily plate direction balances protein, color, grain, and a routine reminder.',
    weeklyStructure: [
      '2 simple breakfasts',
      '2 plate-style lunches',
      '3 flexible dinners',
      '1 leftovers slot',
    ],
    shoppingDirection: ['protein variety', 'colorful produce', 'easy carbs', 'snacks with structure'],
    nextAction: 'Continue into the plate flow when you want to see the day-level structure.',
  },
  decision_fatigue: {
    plateDirection: 'Choose one reliable anchor first, then rotate sides instead of rebuilding meals.',
    weeklyStructure: [
      '1 default breakfast',
      '2 lunch templates',
      '2 no-decision dinners',
      '1 flexible reset meal',
    ],
    shoppingDirection: ['ready proteins', 'pre-cut color', 'pantry fallback', 'routine reminders'],
    nextAction: 'Save the preview direction, then use progress check-ins to refine the routine later.',
  },
  shopping: {
    plateDirection: 'Translate check-in intent into meal anchors first, then shop around those anchors.',
    weeklyStructure: [
      '3 planned breakfasts',
      '2 packable lunches',
      '3 dinner anchors',
      '1 shopping review slot',
    ],
    shoppingDirection: ['core proteins', 'vegetables/fruit', 'grains/pantry', 'batch-prep extras'],
    nextAction: 'Unlock weekly planning when you are ready to save and reuse the plan structure.',
  },
};

export const timeNotes: Record<PlanningTimeId, string> = {
  quick: 'Keep the preview light: fast anchors, low prep, no complicated cooking path.',
  standard: 'Use the standard rhythm: enough prep for variety without turning the week into a project.',
  batch: 'Batch-prep mode highlights repeatable proteins, grains, and produce that can be reused.',
  flexible: 'Flexible cooking keeps the structure loose so you can adjust without losing the plan.',
};

export const forbiddenMedicalClaimPattern =
  /\b(diagnos(?:e|es|ed|ing|is)|treat(?:s|ed|ing)?|cure(?:s|d|ing)?|guaranteed weight loss|AI doctor|personalized medical recommendation(?:s)?|clinically proven|prescription(?:s)?|disease management|medical-grade|therapeutic recommendation(?:s)?)\b/i;

export function getPlanningIntent(intentId: PlanningIntentId): PlanningIntent {
  return planningIntents.find((intent) => intent.id === intentId) ?? planningIntents[0];
}

export function getPlanningTime(timeId: PlanningTimeId): PlanningTime {
  return planningTimes.find((time) => time.id === timeId) ?? planningTimes[0];
}

export function isPlanningIntentId(value: unknown): value is PlanningIntentId {
  return typeof value === 'string' && planningIntents.some((intent) => intent.id === value);
}

export function isPlanningTimeId(value: unknown): value is PlanningTimeId {
  return typeof value === 'string' && planningTimes.some((time) => time.id === value);
}

export function isValidGuidedPlanningDraft(value: unknown): value is GuidedPlanningDraft {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const draft = value as { intentId?: unknown; timeId?: unknown; savedAt?: unknown };
  return (
    isPlanningIntentId(draft.intentId) &&
    isPlanningTimeId(draft.timeId) &&
    (draft.savedAt === undefined || typeof draft.savedAt === 'string')
  );
}

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, Hero, StatsCard, buttonClasses } from '../components/ui';

type PlanningIntentId = 'consistent' | 'balanced' | 'decision_fatigue' | 'shopping';
type PlanningTimeId = 'quick' | 'standard' | 'batch' | 'flexible';

interface PlanningIntent {
  id: PlanningIntentId;
  label: string;
  helper: string;
}

interface PlanningTime {
  id: PlanningTimeId;
  label: string;
  helper: string;
}

interface PlanningPreview {
  plateDirection: string;
  weeklyStructure: string[];
  shoppingDirection: string[];
  nextAction: string;
}

const planningIntents: PlanningIntent[] = [
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

const planningTimes: PlanningTime[] = [
  { id: 'quick', label: '10–15 min meals', helper: 'Smallest next step.' },
  { id: 'standard', label: 'Standard meal window', helper: 'Balanced prep window.' },
  { id: 'batch', label: 'Batch prep', helper: 'Repeatable anchors.' },
  { id: 'flexible', label: 'Flexible cooking', helper: 'Loose weekly plan.' },
];

const previewByIntent: Record<PlanningIntentId, PlanningPreview> = {
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

const timeNotes: Record<PlanningTimeId, string> = {
  quick: 'Keep the preview light: fast anchors, low prep, no complicated cooking path.',
  standard: 'Use the standard rhythm: enough prep for variety without turning the week into a project.',
  batch: 'Batch-prep mode highlights repeatable proteins, grains, and produce that can be reused.',
  flexible: 'Flexible cooking keeps the structure loose so you can adjust without losing the plan.',
};

const forbiddenMedicalClaimPattern =
  /\b(diagnose|treat|cure|guaranteed weight loss|AI doctor|personalized medical recommendation|clinically proven|prescription|disease management|medical-grade|therapeutic recommendation)\b/i;

function OptionButton({
  isSelected,
  label,
  helper,
  onClick,
}: {
  isSelected: boolean;
  label: string;
  helper: string;
  onClick: () => void;
}): JSX.Element {
  return (
    <button
      type="button"
      aria-pressed={isSelected}
      onClick={onClick}
      className={[
        'min-h-[5.5rem] rounded-2xl border p-4 text-left transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)] motion-reduce:transition-none',
        isSelected
          ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/18 shadow-[0_16px_40px_rgba(51,159,255,0.16)]'
          : 'border-white/12 bg-white/[0.07] hover:border-white/22 hover:bg-white/[0.1]',
      ].join(' ')}
    >
      <span className="flex items-center justify-between gap-3">
        <span className="text-sm font-semibold text-white">{label}</span>
        <span className="rounded-full bg-white/10 px-2 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-white/72">
          {isSelected ? 'Selected' : 'Choose'}
        </span>
      </span>
      <span className="mt-2 block text-xs leading-5 text-white/64">{helper}</span>
    </button>
  );
}

function ValueRailCard({ title, detail, badge }: { title: string; detail: string; badge: string }): JSX.Element {
  return (
    <div className="rounded-2xl border border-white/12 bg-white/[0.07] p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/46">{badge}</p>
      <h3 className="mt-2 text-base font-semibold text-white">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-white/64">{detail}</p>
    </div>
  );
}

export default function Home(): JSX.Element {
  const [selectedIntent, setSelectedIntent] = useState<PlanningIntentId>('consistent');
  const [selectedTime, setSelectedTime] = useState<PlanningTimeId>('standard');
  const preview = previewByIntent[selectedIntent];
  const copyCorpus = [
    ...planningIntents.map((intent) => `${intent.label} ${intent.helper}`),
    ...planningTimes.map((time) => `${time.label} ${time.helper}`),
    preview.plateDirection,
    ...preview.weeklyStructure,
    ...preview.shoppingDirection,
    preview.nextAction,
    timeNotes[selectedTime],
  ].join(' ');

  if (forbiddenMedicalClaimPattern.test(copyCorpus)) {
    throw new Error('Guided Planning Preview contains forbidden medical claim copy.');
  }

  return (
    <main className="min-h-screen bg-[var(--pp-navy)] px-4 py-6 text-white sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-8" data-testid="guided-planning-preview">
        <Hero
          eyebrow="Guided Planning Preview"
          title="Turn a check-in into practical meal decisions."
          description="PulsePlate connects your planning intent to a simple plate direction, weekly rhythm, shopping direction, and the next click. This is a planning preview, not a final personalized plan."
          chips={
            <>
              <span className="rounded-full bg-white/[0.08] px-4 py-2 text-xs font-semibold text-white/88">
                FREE preview
              </span>
              <span className="rounded-full bg-white/[0.08] px-4 py-2 text-xs font-semibold text-white/88">
                PRO saves weekly plans
              </span>
              <span className="rounded-full bg-white/[0.08] px-4 py-2 text-xs font-semibold text-white/88">
                VIP unlocks menu flows
              </span>
            </>
          }
          actions={
            <>
              <Link
                to="/setup"
                data-testid="primary-planning-cta"
                className={buttonClasses({
                  className: 'rounded-2xl text-[var(--color-primary-foreground)]',
                  size: 'lg',
                })}
              >
                Continue planning
              </Link>
              <a
                href="#wellness-boundary"
                className={buttonClasses({
                  variant: 'secondary',
                  className: 'rounded-2xl border-white/14 bg-white/[0.08] text-white hover:bg-white/[0.12]',
                  size: 'lg',
                })}
              >
                Learn why this is wellness-only
              </a>
            </>
          }
          aside={
            <div className="rounded-[1.5rem] border border-white/12 bg-[var(--color-surface)]/10 p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/48">Product path</p>
              <ol className="mt-4 space-y-3 text-sm text-white/72">
                {['check-in', 'targets', 'daily plate', 'weekly plan', 'shopping list'].map((step, index) => (
                  <li key={step} className="flex items-center gap-3">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white/10 text-xs font-semibold text-white">
                      {index + 1}
                    </span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          }
        />

        <section className="grid gap-4 sm:grid-cols-3" aria-label="Planning value summary">
          <StatsCard align="left" detail="Check-in and preview" label="FREE" tone="inverse" value="Baseline" />
          <StatsCard align="left" detail="Targets and saved weekly planning" label="PRO" tone="inverse" value="Structure" />
          <StatsCard align="left" detail="Recipes, menu flows, shopping/export" label="VIP" tone="inverse" value="Action" />
        </section>

        <section className="grid gap-8 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
          <div className="space-y-6">
            <Card className="rounded-[2rem] border-white/12 bg-white/[0.06] text-white shadow-none">
              <CardContent className="space-y-4 p-5 sm:p-6" data-testid="planning-intent-selector">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/46">Step 1</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-white">Choose your planning intent</h2>
                  <p className="mt-2 text-sm leading-6 text-white/64">
                    Start with the reason you opened PulsePlate today.
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {planningIntents.map((intent) => (
                    <OptionButton
                      key={intent.id}
                      isSelected={selectedIntent === intent.id}
                      label={intent.label}
                      helper={intent.helper}
                      onClick={() => setSelectedIntent(intent.id)}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-[2rem] border-white/12 bg-white/[0.06] text-white shadow-none">
              <CardContent className="space-y-4 p-5 sm:p-6" data-testid="planning-time-selector">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/46">Step 2</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-white">Pick a practical constraint</h2>
                  <p className="mt-2 text-sm leading-6 text-white/64">
                    The preview adapts its planning language to your cooking window.
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {planningTimes.map((time) => (
                    <OptionButton
                      key={time.id}
                      isSelected={selectedTime === time.id}
                      label={time.label}
                      helper={time.helper}
                      onClick={() => setSelectedTime(time.id)}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card className="rounded-[2rem] border-[var(--color-primary)]/45 bg-[var(--color-primary)]/12 text-white shadow-[0_30px_70px_rgba(51,159,255,0.14)]">
              <CardContent className="space-y-5 p-5 sm:p-6" data-testid="planning-preview-card">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/52">Planning preview</p>
                    <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-white">Your next meal rhythm</h2>
                  </div>
                  <span className="rounded-full bg-white/12 px-3 py-2 text-xs font-semibold text-white/78">
                    Preview example
                  </span>
                </div>

                <section aria-labelledby="plate-direction-heading" className="rounded-2xl bg-white/[0.08] p-4">
                  <h3 id="plate-direction-heading" className="text-sm font-semibold text-white">
                    Today’s plate direction
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-white/70">{preview.plateDirection}</p>
                  <p className="mt-3 text-xs font-semibold text-white/54">{timeNotes[selectedTime]}</p>
                </section>

                <section aria-labelledby="weekly-structure-heading" className="grid gap-4 sm:grid-cols-2">
                  <div className="rounded-2xl bg-white/[0.08] p-4">
                    <h3 id="weekly-structure-heading" className="text-sm font-semibold text-white">
                      Weekly structure
                    </h3>
                    <ul className="mt-3 space-y-2 text-sm text-white/70">
                      {preview.weeklyStructure.map((item) => (
                        <li key={item} className="flex gap-2">
                          <span aria-hidden="true" className="text-[var(--color-success)]">•</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="rounded-2xl bg-white/[0.08] p-4">
                    <h3 className="text-sm font-semibold text-white">Shopping direction</h3>
                    <ul className="mt-3 space-y-2 text-sm text-white/70">
                      {preview.shoppingDirection.map((item) => (
                        <li key={item} className="flex gap-2">
                          <span aria-hidden="true" className="text-[var(--color-success)]">•</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </section>

                <div className="rounded-2xl border border-white/12 bg-[var(--pp-navy)]/40 p-4">
                  <h3 className="text-sm font-semibold text-white">Next action</h3>
                  <p className="mt-2 text-sm leading-6 text-white/70">{preview.nextAction}</p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <Link
                      to="/plate"
                      className={buttonClasses({
                        variant: 'secondary',
                        className: 'rounded-2xl border-white/14 bg-white/[0.08] text-white hover:bg-white/[0.12]',
                      })}
                    >
                      Continue into the plate flow
                    </Link>
                    <Link
                      to="/progress"
                      className={buttonClasses({
                        variant: 'ghost',
                        className: 'rounded-2xl text-white hover:bg-white/[0.1]',
                      })}
                    >
                      Use progress check-ins
                    </Link>
                    <Link
                      to="/pro"
                      className={buttonClasses({
                        variant: 'ghost',
                        className: 'rounded-2xl text-white hover:bg-white/[0.1]',
                      })}
                    >
                      Unlock weekly planning
                    </Link>
                  </div>
                </div>
              </CardContent>
            </Card>

            <section className="grid gap-3" data-testid="tier-value-rail" aria-label="FREE PRO VIP value ladder">
              <ValueRailCard
                badge="FREE"
                title="Check-in and baseline preview"
                detail="Understand the planning direction before committing to a saved weekly flow."
              />
              <ValueRailCard
                badge="PRO"
                title="Targets, daily plate, saved weekly plan"
                detail="Move from preview into reusable planning structure when you are ready."
              />
              <ValueRailCard
                badge="VIP"
                title="Recipes, menu flows, shopping/export"
                detail="Turn planning into action surfaces once the core rhythm is stable."
              />
            </section>

            <Card
              id="wellness-boundary"
              className="rounded-[2rem] border-white/12 bg-white/[0.06] text-white shadow-none"
            >
              <CardContent className="space-y-3 p-5" data-testid="wellness-boundary-note">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/46">Wellness boundary</p>
                <h2 className="text-xl font-semibold text-white">Wellness planning support only. Not medical advice.</h2>
                <p className="text-sm leading-6 text-white/66">
                  This preview helps organize meal decisions in a wellness context. It is not clinical guidance and is not a substitute for qualified professional care.
                </p>
              </CardContent>
            </Card>
          </div>
        </section>
      </div>
    </main>
  );
}

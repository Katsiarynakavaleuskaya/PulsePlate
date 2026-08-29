import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, Hero, StatsCard, buttonClasses } from '../components/ui';
import {
  forbiddenMedicalClaimPattern,
  planningIntents,
  planningTimes,
  previewByIntent,
  timeNotes,
  type PlanningIntentId,
  type PlanningTimeId,
} from '../features/guidedPlanning/planningPreview';
import { SupportChoiceCard } from '../features/fitchef/SupportChoiceCard';
import { useAuth } from '../lib/auth';
import { trackGuidedPlanningEvent, type GuidedPlanningEventPayload } from '../lib/mvpObservability';
import { useSettings } from '../lib/settings';

type PlanningAuthState = NonNullable<GuidedPlanningEventPayload['authState']>;

function OptionButton({
  isSelected,
  label,
  helper,
  controls,
  onClick,
}: {
  isSelected: boolean;
  label: string;
  helper: string;
  controls: string;
  onClick: () => void;
}): JSX.Element {
  return (
    <button
      type="button"
      aria-pressed={isSelected}
      aria-controls={controls}
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
  const { isAuthenticated, isLoading } = useAuth();
  const { updateSetting } = useSettings();
  const [selectedIntent, setSelectedIntent] = useState<PlanningIntentId>('consistent');
  const [selectedTime, setSelectedTime] = useState<PlanningTimeId>('standard');
  const [isPreviewSaved, setIsPreviewSaved] = useState(false);
  const unauthenticatedPromptViewedRef = useRef(false);
  const preview = previewByIntent[selectedIntent];
  const authState: PlanningAuthState = isLoading ? 'unknown' : isAuthenticated ? 'authenticated' : 'unauthenticated';
  const isKnownAuthenticated = authState === 'authenticated';
  const progressMessage = isPreviewSaved
    ? 'Preview marked for this app session. Continue when you are ready to turn this direction into weekly planning.'
    : 'Planning progress starts with your selected intent and practical cooking window.';
  const progressAuthMessage = isKnownAuthenticated
    ? 'Your signed-in session can continue this planning direction into protected PulsePlate flows.'
    : authState === 'unknown'
      ? 'Checking your session before PulsePlate routes this preview into protected planning flows.'
      : 'Sign in to continue this planning direction through protected flows. This preview mark stays in the current app session only.';
  const savePromptLabel = isKnownAuthenticated
    ? 'Continue marked direction'
    : authState === 'unknown'
      ? 'Checking session'
      : 'Save preview';
  const savePromptCopy = isKnownAuthenticated
    ? 'Your planning direction is ready. PulsePlate can mark this preview in the current app session before you continue.'
    : authState === 'unknown'
      ? 'PulsePlate is checking whether this preview can continue through a signed-in planning session.'
      : 'Without sign-in, PulsePlate can only mark this preview in the current app session.';
  const saveButtonLabel = isPreviewSaved
    ? 'Preview marked for session'
    : isKnownAuthenticated
      ? 'Mark preview ready for session'
      : 'Mark preview for session';
  const copyCorpus = [
    ...planningIntents.map((intent) => `${intent.label} ${intent.helper}`),
    ...planningTimes.map((time) => `${time.label} ${time.helper}`),
    preview.plateDirection,
    ...preview.weeklyStructure,
    ...preview.shoppingDirection,
    preview.nextAction,
    timeNotes[selectedTime],
    progressMessage,
    progressAuthMessage,
    savePromptLabel,
    savePromptCopy,
    saveButtonLabel,
  ].join(' ');

  useEffect(() => {
    trackGuidedPlanningEvent('guided_planning_viewed', {
      surface: 'app',
      componentId: 'guided-planning-preview',
      routePath: '/app',
    });
    trackGuidedPlanningEvent('planning_preview_seen', {
      surface: 'app',
      componentId: 'planning-preview-card',
      routePath: '/app',
    });
    (['FREE', 'PRO', 'VIP'] as const).forEach((tierLabel) => {
      trackGuidedPlanningEvent('tier_value_viewed', {
        surface: 'app',
        componentId: 'tier-value-rail',
        routePath: '/app',
        tierLabel,
      });
    });
    trackGuidedPlanningEvent('wellness_boundary_viewed', {
      surface: 'app',
      componentId: 'wellness-boundary-note',
      routePath: '/app',
    });
  }, []);

  useEffect(() => {
    trackGuidedPlanningEvent('planning_progress_state_viewed', {
      surface: 'app',
      componentId: 'planning-progress-state',
      routePath: '/app',
      optionId: isPreviewSaved ? 'screen_preview_marked' : 'preview_ready',
      authState,
    });
  }, [authState, isPreviewSaved]);

  useEffect(() => {
    if (authState === 'unauthenticated' && !unauthenticatedPromptViewedRef.current) {
      unauthenticatedPromptViewedRef.current = true;
      trackGuidedPlanningEvent('planning_save_prompt_viewed', {
        surface: 'app',
        componentId: 'planning-save-auth-prompt',
        routePath: '/app',
        authState,
      });
      trackGuidedPlanningEvent('planning_auth_prompt_viewed', {
        surface: 'app',
        componentId: 'planning-save-auth-prompt',
        routePath: '/app',
        authState,
      });
    }
  }, [authState]);

  if (forbiddenMedicalClaimPattern.test(copyCorpus)) {
    throw new Error('Guided Planning Preview contains forbidden medical claim copy.');
  }

  function selectIntent(intentId: PlanningIntentId): void {
    if (intentId !== selectedIntent) {
      setIsPreviewSaved(false);
      updateSetting('guidedPlanningDraft', undefined);
    }
    setSelectedIntent(intentId);
    trackGuidedPlanningEvent('planning_intent_selected', {
      surface: 'app',
      componentId: 'planning-intent-selector',
      routePath: '/app',
      optionId: intentId,
    });
  }

  function selectTime(timeId: PlanningTimeId): void {
    if (timeId !== selectedTime) {
      setIsPreviewSaved(false);
      updateSetting('guidedPlanningDraft', undefined);
    }
    setSelectedTime(timeId);
    trackGuidedPlanningEvent('planning_time_selected', {
      surface: 'app',
      componentId: 'planning-time-selector',
      routePath: '/app',
      optionId: timeId,
    });
  }

  function trackPrimaryPlanningCta(): void {
    persistGuidedPlanningDraft();
    trackGuidedPlanningEvent('primary_planning_cta_clicked', {
      surface: 'app',
      componentId: 'primary-planning-cta',
      routePath: '/setup',
    });
  }

  function savePlanningPreview(): void {
    setIsPreviewSaved(true);
    persistGuidedPlanningDraft();
    trackGuidedPlanningEvent('planning_save_clicked', {
      surface: 'app',
      componentId: 'planning-save-cta',
      routePath: '/app',
      optionId: selectedIntent,
      authState,
    });
  }

  function trackContinuePlanning(routePath: '/plate' | '/progress'): void {
    persistGuidedPlanningDraft();
    trackGuidedPlanningEvent('planning_continue_clicked', {
      surface: 'app',
      componentId: 'planning-continue-cta',
      routePath,
      optionId: selectedTime,
      authState,
    });
  }

  function persistGuidedPlanningDraft(): void {
    updateSetting('guidedPlanningDraft', {
      intentId: selectedIntent,
      timeId: selectedTime,
      savedAt: new Date().toISOString(),
    });
  }

  return (
    <main className="min-h-screen bg-[var(--pp-navy)] px-4 py-6 text-white sm:px-6 lg:px-8">
      <div
        className="mx-auto max-w-6xl space-y-8"
        data-testid="guided-planning-preview"
        aria-describedby="mvp-accessibility-evidence mvp-observability-evidence"
      >
        <p id="mvp-accessibility-evidence" className="sr-only" data-testid="mvp-accessibility-evidence">
          Guided Planning Preview exposes named selector groups, selected states, preview landmarks, and a wellness-only boundary for assistive technology.
        </p>
        <p id="mvp-observability-evidence" className="sr-only" data-testid="mvp-observability-evidence">
          Guided Planning Preview emits frontend-only interaction evidence without backend analytics, cookies, storage, or health identifiers.
        </p>
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
                onClick={trackPrimaryPlanningCta}
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
                  <h2 id="planning-intent-heading" className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-white">Choose your planning intent</h2>
                  <p className="mt-2 text-sm leading-6 text-white/64">
                    Start with the reason you opened PulsePlate today.
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2" role="group" aria-labelledby="planning-intent-heading">
                  {planningIntents.map((intent) => (
                    <OptionButton
                      key={intent.id}
                      isSelected={selectedIntent === intent.id}
                      label={intent.label}
                      helper={intent.helper}
                      controls="planning-preview-card-region"
                      onClick={() => selectIntent(intent.id)}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-[2rem] border-white/12 bg-white/[0.06] text-white shadow-none">
              <CardContent className="space-y-4 p-5 sm:p-6" data-testid="planning-time-selector">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/46">Step 2</p>
                  <h2 id="planning-time-heading" className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-white">Pick a practical constraint</h2>
                  <p className="mt-2 text-sm leading-6 text-white/64">
                    The preview adapts its planning language to your cooking window.
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2" role="group" aria-labelledby="planning-time-heading">
                  {planningTimes.map((time) => (
                    <OptionButton
                      key={time.id}
                      isSelected={selectedTime === time.id}
                      label={time.label}
                      helper={time.helper}
                      controls="planning-preview-card-region"
                      onClick={() => selectTime(time.id)}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card className="rounded-[2rem] border-[var(--color-primary)]/45 bg-[var(--color-primary)]/12 text-white shadow-[0_30px_70px_rgba(51,159,255,0.14)]">
              <CardContent
                id="planning-preview-card-region"
                role="region"
                aria-labelledby="planning-preview-heading"
                className="space-y-5 p-5 sm:p-6"
                data-testid="planning-preview-card"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/52">Planning preview</p>
                    <h2 id="planning-preview-heading" className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-white">Your next meal rhythm</h2>
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
                  <div
                    className="mt-4 rounded-2xl border border-white/12 bg-white/[0.07] p-4"
                    data-testid="planning-progress-state"
                    role="status"
                    aria-live="polite"
                  >
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/46">
                      Planning progress
                    </p>
                    <p className="mt-2 text-sm leading-6 text-white/72">{progressMessage}</p>
                    <p className="mt-2 text-xs font-semibold text-white/58">
                      {progressAuthMessage}
                    </p>
                  </div>
                  <div
                    className="mt-4 rounded-2xl border border-white/12 bg-white/[0.06] p-4"
                    data-testid="planning-save-auth-prompt"
                  >
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/46">
                      {savePromptLabel}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-white/68">
                      {savePromptCopy}
                    </p>
                    <div className="mt-4 flex flex-wrap gap-3">
                      <button
                        type="button"
                        data-testid="planning-save-cta"
                        onClick={savePlanningPreview}
                        className={buttonClasses({
                          variant: 'secondary',
                          className: 'rounded-2xl border-white/14 bg-white/[0.08] text-white hover:bg-white/[0.12]',
                        })}
                      >
                        {saveButtonLabel}
                      </button>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <Link
                      to="/plate"
                      data-testid="planning-continue-cta"
                      onClick={() => trackContinuePlanning('/plate')}
                      className={buttonClasses({
                        variant: 'secondary',
                        className: 'rounded-2xl border-white/14 bg-white/[0.08] text-white hover:bg-white/[0.12]',
                      })}
                    >
                      Continue into the plate flow
                    </Link>
                    <Link
                      to="/progress"
                      onClick={() => trackContinuePlanning('/progress')}
                      className={buttonClasses({
                        variant: 'ghost',
                        className: 'rounded-2xl text-white hover:bg-white/[0.1]',
                      })}
                    >
                      Use progress check-ins
                    </Link>
                    <Link
                      to="/marketing"
                      className={buttonClasses({
                        variant: 'ghost',
                        className: 'rounded-2xl text-white hover:bg-white/[0.1]',
                      })}
                    >
                      Learn about PulsePlate for Apple devices
                    </Link>
                  </div>
                </div>
              </CardContent>
            </Card>

            <SupportChoiceCard authState={authState} />

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
              role="note"
              aria-labelledby="wellness-boundary-heading"
              className="rounded-[2rem] border-white/12 bg-white/[0.06] text-white shadow-none"
            >
              <CardContent className="space-y-3 p-5" data-testid="wellness-boundary-note">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/46">Wellness boundary</p>
                <h2 id="wellness-boundary-heading" className="text-xl font-semibold text-white">Wellness planning support only. Not medical advice.</h2>
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

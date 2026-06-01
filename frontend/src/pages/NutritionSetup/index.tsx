// RU: Контейнер страницы Nutrition Setup - анкета → результаты
// EN: Nutrition Setup page container - form → results

import { useState, useEffect } from 'react';
import SetupForm from './SetupForm';
import ResultView from './ResultView';
import type { SetupFormValues } from './schema';
import { isValidSetupFormValues } from './schema';
import { useSettings } from '../../lib/settings';
import { Stepper } from '../../components/ui';
import { useTranslation } from 'react-i18next';
import {
  getPlanningIntent,
  getPlanningTime,
  isValidGuidedPlanningDraft,
  previewByIntent,
  timeNotes,
  type GuidedPlanningDraft,
} from '../../features/guidedPlanning/planningPreview';

function PlanningDirectionPanel({ draft }: { draft: GuidedPlanningDraft }): JSX.Element {
  const { t } = useTranslation();
  const intent = getPlanningIntent(draft.intentId);
  const time = getPlanningTime(draft.timeId);
  const preview = previewByIntent[draft.intentId];

  return (
    <section
      aria-labelledby="planning-direction-heading"
      className="mb-6 rounded-lg border border-primary/20 bg-white p-4 shadow-sm sm:p-5"
      data-testid="planning-direction-panel"
    >
      <p className="text-xs font-semibold uppercase text-muted">
        {t('nutritionSetup.guidedPlanning.direction.eyebrow')}
      </p>
      <h2 id="planning-direction-heading" className="mt-2 text-lg font-semibold text-text">
        {intent.label}
      </h2>
      <p className="mt-2 text-sm leading-6 text-muted">{preview.plateDirection}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-md bg-navy/5 p-3">
          <p className="text-xs font-semibold uppercase text-muted">
            {t('nutritionSetup.guidedPlanning.direction.cookingWindow')}
          </p>
          <p className="mt-1 text-sm font-medium text-text">{time.label}</p>
          <p className="mt-1 text-xs leading-5 text-muted">{timeNotes[draft.timeId]}</p>
        </div>
        <div className="rounded-md bg-navy/5 p-3">
          <p className="text-xs font-semibold uppercase text-muted">
            {t('nutritionSetup.guidedPlanning.direction.nextStep')}
          </p>
          <p className="mt-1 text-sm leading-5 text-text">{preview.nextAction}</p>
        </div>
      </div>
    </section>
  );
}

export default function NutritionSetupPage() {
  const { settings } = useSettings();
  const { t } = useTranslation();
  const [values, setValues] = useState<SetupFormValues | null>(null);
  const guidedPlanningDraft = isValidGuidedPlanningDraft(settings.guidedPlanningDraft)
    ? settings.guidedPlanningDraft
    : undefined;
  const currentStep = values ? 1 : 0;
  const setupSteps = [
    {
      id: 'profile',
      label: t('nutritionSetup.steps.profile.label'),
      description: t('nutritionSetup.steps.profile.description'),
    },
    {
      id: 'results',
      label: t('nutritionSetup.steps.results.label'),
      description: t('nutritionSetup.steps.results.description'),
    },
  ];

  // Initialize values from saved settings on mount
  useEffect(() => {
    if (isValidSetupFormValues(settings.setup)) {
      setValues(settings.setup);
    } else {
      setValues(null);
    }
  }, [settings.setup]);

  return (
    <div className="max-w-4xl mx-auto p-4 pb-20">
      <Stepper
        ariaLabel={t('nutritionSetup.steps.ariaLabel')}
        className="mb-6"
        currentStep={currentStep}
        progressLabel={t('nutritionSetup.steps.progressLabel', {
          current: currentStep + 1,
          total: setupSteps.length,
        })}
        steps={[...setupSteps]}
      />
      {guidedPlanningDraft ? <PlanningDirectionPanel draft={guidedPlanningDraft} /> : null}
      {!values ? (
        <SetupForm onSubmit={setValues} />
      ) : (
        <ResultView
          guidedPlanningDraft={guidedPlanningDraft}
          values={values}
          onEdit={() => setValues(null)}
        />
      )}
    </div>
  );
}

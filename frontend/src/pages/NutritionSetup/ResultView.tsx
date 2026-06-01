// RU: Компонент отображения результатов расчета - тарелка + макро/микро/вода
// EN: Results display component - plate + macro/micro/water

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import * as setupHooks from './hooks';
import PlateChart from './PlateChart';
import MacroCards from './MacroCards';
import WaterCard from './WaterCard';
import MicrosGrid from './MicrosGrid';
import type { SetupFormValues } from './schema';
import { buttonClasses, StatsCard } from '../../components/ui';
import {
  getPlanningIntent,
  getPlanningTime,
  previewByIntent,
  type GuidedPlanningDraft,
} from '../../features/guidedPlanning/planningPreview';

interface ResultViewProps {
  guidedPlanningDraft?: GuidedPlanningDraft;
  values: SetupFormValues;
  onEdit: () => void;
}

function GuidedPlanningNextSteps({ draft }: { draft: GuidedPlanningDraft }): JSX.Element {
  const { t } = useTranslation();
  const intent = getPlanningIntent(draft.intentId);
  const time = getPlanningTime(draft.timeId);
  const preview = previewByIntent[draft.intentId];

  return (
    <nav
      aria-label={t('nutritionSetup.guidedPlanning.nextSteps.ariaLabel')}
      className="rounded-lg border border-primary/20 bg-white p-4 shadow-sm sm:p-5"
      data-testid="guided-planning-next-steps"
    >
      <p className="text-xs font-semibold uppercase text-muted">
        {t('nutritionSetup.guidedPlanning.nextSteps.eyebrow')}
      </p>
      <h2 className="mt-2 text-lg font-semibold text-text">{intent.label}</h2>
      <p className="mt-2 text-sm leading-6 text-muted">
        {t('nutritionSetup.guidedPlanning.nextSteps.detail', {
          timeLabel: time.label,
          nextAction: preview.nextAction,
        })}
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        <Link
          to="/plate"
          className={buttonClasses({
            className: 'rounded-lg text-navy',
          })}
        >
          {t('nutritionSetup.guidedPlanning.nextSteps.plateLink')}
        </Link>
        <Link
          to="/progress"
          className={buttonClasses({
            variant: 'secondary',
            className: 'rounded-lg',
          })}
        >
          {t('nutritionSetup.guidedPlanning.nextSteps.progressLink')}
        </Link>
      </div>
    </nav>
  );
}

export default function ResultView({ guidedPlanningDraft, values, onEdit }: ResultViewProps) {
  const { t, i18n } = useTranslation();
  const [retryKey, setRetryKey] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);

  const browserLang = typeof navigator !== 'undefined' ? navigator.language : undefined;
  const currentLang = setupHooks.resolveSetupLang(undefined, i18n.language, browserLang);

  const { bmrData, plateData, loading, error } = setupHooks.useSetupCalc(values, currentLang, retryKey);
  const {
    data: targetsData,
    loading: targetsLoading,
    error: targetsError,
  } = setupHooks.useTargets(values, currentLang, retryKey);

  const handleRetry = () => {
    setIsRetrying(true);
    setRetryKey(prev => prev + 1);
  };

  // Reset retry state when loading completes
  useEffect(() => {
    if (!loading && !targetsLoading && isRetrying) {
      setIsRetrying(false);
    }
  }, [loading, targetsLoading, isRetrying]);

  if (loading || targetsLoading || isRetrying) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted">
            {isRetrying ? t('common.retrying') : t('nutrition.loadingPlate')}
          </p>
        </div>
      </div>
    );
  }

  if (error || targetsError || !bmrData || !plateData) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm text-center">
        <div className="text-red-600 mb-4">
          <svg className="w-12 h-12 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <h2 className="text-xl font-semibold text-text mb-2">{t('nutrition.error.title')}</h2>
        <p className="text-muted mb-6">
          {error || targetsError || t('nutrition.error.description')}
        </p>
        <div className="flex gap-4 justify-center">
          <button
            onClick={handleRetry}
            disabled={isRetrying}
            className="px-6 py-3 bg-primary text-navy rounded-xl font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isRetrying ? t('common.retrying') : t('common.tryAgain')}
          </button>
          <button
            onClick={onEdit}
            className="px-6 py-3 bg-muted/20 text-text rounded-xl font-medium hover:bg-muted/30 transition-colors"
          >
            {t('nutrition.error.editButton')}
          </button>
        </div>
      </div>
    );
  }

  const fallbackWaterLiters = Number.isFinite(values.weight_kg)
    ? Math.max(1.5, Number((values.weight_kg * 0.03).toFixed(1)))
    : 2;
  const waterLiters = targetsData?.water_l ?? plateData.water_l ?? fallbackWaterLiters;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-text">{t('nutrition.header.title')}</h1>
            <p className="text-muted mt-1">{t('nutrition.header.subtitle')}</p>
          </div>
          <button
            onClick={onEdit}
            className="px-4 py-2 text-primary hover:text-primary/80 underline font-medium transition-colors"
          >
            {t('nutrition.header.editButton')}
          </button>
        </div>

        {/* BMR/TDEE Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-navy/5 rounded-xl">
          <StatsCard align="center" label={t('nutrition.summary.bmr')} value={Math.round(bmrData.bmr)} />
          <StatsCard align="center" label={t('nutrition.summary.tdee')} value={Math.round(bmrData.tdee)} />
          <StatsCard align="center" label={t('nutrition.summary.goal')} value={Math.round(plateData.plate.kcal)} />
          <StatsCard align="center" label={t('nutrition.summary.method')} value={bmrData.method} />
        </div>
      </div>

      {guidedPlanningDraft ? <GuidedPlanningNextSteps draft={guidedPlanningDraft} /> : null}

      {/* Plate Chart and Macros */}
      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-1">
          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-text mb-4 text-center">{t('nutrition.macros.title')}</h2>
            <PlateChart
              carbsPct={plateData.plate.carbs_pct}
              proteinPct={plateData.plate.protein_pct}
              fatPct={plateData.plate.fat_pct}
            />
          </div>
        </div>

        <div className="md:col-span-2 space-y-6">
          <MacroCards
            kcal={plateData.plate.kcal}
            carbsG={plateData.macros.carbs_g}
            proteinG={plateData.macros.protein_g}
            fatG={plateData.macros.fat_g}
            fiberG={plateData.macros.fiber_g}
            bmr={bmrData.bmr}
            tdee={bmrData.tdee}
          />

          <WaterCard liters={waterLiters} />
        </div>
      </div>

      {/* Micros */}
      {targetsData && (
        <div className="bg-white rounded-2xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-text mb-4">{t('nutrition.micros.title')}</h2>
          <p className="text-muted mb-6 text-sm">
            {t('nutrition.micros.description')}
          </p>
          <MicrosGrid items={targetsData.micros} />
        </div>
      )}
    </div>
  );
}

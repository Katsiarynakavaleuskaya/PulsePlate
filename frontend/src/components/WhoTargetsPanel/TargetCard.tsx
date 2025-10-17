import { useTranslation } from 'react-i18next';
import { clsx } from 'clsx';
import type { TargetsApiResponse } from '../../api/premium/types';
import { MICRO_CONFIG } from '../../pages/NutritionSetup/hooks';

// Helper function for consistent numeric formatting
function formatNumericValue(value: unknown): string {
  if (value == null) return '—';
  return typeof value === 'number' ? value.toLocaleString() : String(value);
}

// Helper function to get micronutrient unit
function getMicronutrientUnit(microKey: string, locale: string): string {
  const meta = MICRO_CONFIG[microKey];
  if (meta && meta.units) {
    return meta.units[locale as keyof typeof meta.units] || meta.units.en;
  }

  // Fallback: extract unit from key name
  if (/_mg$/i.test(microKey)) {
    return locale === 'ru' ? 'мг' : 'mg';
  } else if (/_ug$/i.test(microKey) || /_(mcg)$/i.test(microKey)) {
    return locale === 'ru' ? 'мкг' : 'mcg';
  } else if (/_iu$/i.test(microKey)) {
    return locale === 'ru' ? 'МЕ' : locale === 'es' ? 'UI' : 'IU';
  }

  return '';
}

// Constants for performance optimization
const MACRO_FIELDS = [
  { key: 'protein', fieldPath: 'protein_g' },
  { key: 'carbs', fieldPath: 'carbs_g' },
  { key: 'fat', fieldPath: 'fat_g' },
  { key: 'fiber', fieldPath: 'fiber_g' },
] as const;

const ACTIVITY_FIELDS = [
  {
    key: 'moderateAerobic',
    fieldPath: 'moderate_aerobic_min',
    unitKey: 'minutes'
  },
  {
    key: 'strength',
    fieldPath: 'strength_sessions',
    unitKey: 'sessions'
  },
  {
    key: 'steps',
    fieldPath: 'steps_daily',
    unitKey: 'stepsUnit'
  },
] as const;

interface TargetCardProps {
  data: TargetsApiResponse;
  className?: string;
}

export function WhoTargetsCards({ data, className }: TargetCardProps) {
  const { t } = useTranslation();

  return (
    <div className={clsx('who-targets-cards', className)}>
      {/* Daily Calories */}
      <div className="target-card target-card--primary">
        <div className="target-card__header">
          <h3 className="target-card__title">
            {t('whoTargets.calories.title', 'Daily Calories')}
          </h3>
          <div className="target-card__value">
            {formatNumericValue(data.kcal_daily)}
            <span className="target-card__unit">
              {t('whoTargets.calories.unit', 'kcal')}
            </span>
          </div>
        </div>
        <p className="target-card__description">
          {t('whoTargets.calories.description', 'Based on your BMR, activity level, and goals')}
        </p>
      </div>

      {/* Macronutrients */}
      <div className="target-card">
        <div className="target-card__header">
          <h3 className="target-card__title">
            {t('whoTargets.macros.title', 'Macronutrients')}
          </h3>
        </div>
        <div className="target-card__content">
          <div className="macro-grid">
            {MACRO_FIELDS.map(({ key, fieldPath }) => {
              const field = data.macros[fieldPath];
              return (
              <div key={key} className="macro-item">
                <span className="macro-item__label">
                  {t(`whoTargets.macros.${key}`, key)}
                </span>
                <span className="macro-item__value">
                  {(() => {
                    const formatted = formatNumericValue(field);
                    return formatted === '—' ? '—' : (
                      <>
                        {formatted}
                        <span className="macro-item__unit">
                          {t('whoTargets.macros.unit', 'g')}
                        </span>
                      </>
                    );
                  })()}
                </span>
              </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Hydration */}
      <div className="target-card">
        <div className="target-card__header">
          <h3 className="target-card__title">
            {t('whoTargets.hydration.title', 'Hydration')}
          </h3>
          <div className="target-card__value">
            {formatNumericValue(data.water_ml)}
            <span className="target-card__unit">
              {t('whoTargets.hydration.unit', 'ml')}
            </span>
          </div>
        </div>
        <p className="target-card__description">
          {t('whoTargets.hydration.description', 'Daily water intake recommendation')}
        </p>
      </div>

      {/* Priority Micronutrients */}
      {Object.keys(data.priority_micros).length > 0 && (
        <div className="target-card">
          <div className="target-card__header">
            <h3 className="target-card__title">
              {t('whoTargets.micros.title', 'Priority Micronutrients')}
            </h3>
          </div>
          <div className="target-card__content">
            <ul className="micros-list">
              {Object.entries(data.priority_micros).map(([micro, value]) => {
                const unit = getMicronutrientUnit(micro, 'en'); // Use 'en' as fallback, could be made dynamic
                return (
                  <li key={micro} className="micros-item">
                    <span className="micros-item__label">
                      {t(`whoTargets.micros.${micro}`, micro)}
                    </span>
                    <span className="micros-item__value">
                      {(() => {
                        const formatted = formatNumericValue(value);
                        return formatted === '—' ? '—' : (
                          <>
                            {formatted}
                            {unit && <span className="micros-item__unit">{unit}</span>}
                          </>
                        );
                      })()}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}

      {/* Activity Goals */}
      <div className="target-card">
        <div className="target-card__header">
          <h3 className="target-card__title">
            {t('whoTargets.activity.title', 'Activity Goals')}
          </h3>
        </div>
        <div className="target-card__content">
          <div className="activity-grid">
            {ACTIVITY_FIELDS.map(({ key, fieldPath, unitKey }) => {
              const field = data.activity_weekly[fieldPath];
              return (
              <div key={key} className="activity-item">
                <span className="activity-item__label">
                  {t(`whoTargets.activity.${key}`, key)}
                </span>
                <span className="activity-item__value">
                  {formatNumericValue(field)}
                  <span className="activity-item__unit">
                    {t(`whoTargets.activity.${unitKey}`, unitKey)}
                  </span>
                </span>
              </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Warnings */}
      {data.warnings && data.warnings.length > 0 && (
        <div className="target-card target-card--warning">
          <div className="target-card__header">
            <h3 className="target-card__title">
              {t('whoTargets.warnings.title', 'Important Notes')}
            </h3>
          </div>
          <div className="target-card__content">
            <ul className="warning-list">
              {data.warnings.map((warning, index) => (
                <li key={index} className="warning-item">
                  <span className="warning-item__icon" aria-hidden="true">⚠️</span>
                  <span className="warning-item__text">
                    {/* Note: warning.message is pre-localized from API */}
                    {warning.message}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

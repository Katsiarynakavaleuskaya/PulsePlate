import { useTranslation } from 'react-i18next';
import { clsx } from 'clsx';
import type { TargetsApiResponse } from '../../api/premium/types';

// Helper function for consistent numeric formatting
function formatNumericValue(value: unknown): string {
  return typeof value === 'number' ? value.toLocaleString() : String(value);
}

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
            {[
              { key: 'protein', field: data.macros.protein_g },
              { key: 'carbs', field: data.macros.carbs_g },
              { key: 'fat', field: data.macros.fat_g },
              { key: 'fiber', field: data.macros.fiber_g },
            ].map(({ key, field }) => (
              <div key={key} className="macro-item">
                <span className="macro-item__label">
                  {t(`whoTargets.macros.${key}`, key)}
                </span>
                <span className="macro-item__value">
                  {formatNumericValue(field)}g
                </span>
              </div>
            ))}
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
              {Object.entries(data.priority_micros).map(([micro, value]) => (
                <li key={micro} className="micros-item">
                  <span className="micros-item__label">
                    {t(`whoTargets.micros.${micro}`, micro)}
                  </span>
                  <span className="micros-item__value">
                    {formatNumericValue(value)}
                  </span>
                </li>
              ))}
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
            {[
              {
                key: 'moderateAerobic',
                field: data.activity_weekly.moderate_aerobic_min,
                unitKey: 'minutes'
              },
              {
                key: 'strength',
                field: data.activity_weekly.strength_sessions,
                unitKey: 'sessions'
              },
              {
                key: 'steps',
                field: data.activity_weekly.steps_daily,
                unitKey: 'stepsUnit'
              },
            ].map(({ key, field, unitKey }) => (
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
            ))}
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
                <li key={`${warning.message}-${index}`} className="warning-item">
                  <span className="warning-item__icon" aria-hidden="true">⚠️</span>
                  <span className="warning-item__text">
                    {/* Note: warning.message is pre-localized from API */}
                    {t(warning.message, warning.message)}
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

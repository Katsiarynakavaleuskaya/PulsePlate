import { useTranslation } from 'react-i18next';
import { clsx } from 'clsx';
import type { TargetsApiResponse } from '../../api/premium/types';

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
            {data.kcal_daily.toLocaleString()}
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
            <div className="macro-item">
              <span className="macro-item__label">
                {t('whoTargets.macros.protein', 'Protein')}
              </span>
              <span className="macro-item__value">
                {typeof data.macros.protein_g === 'number'
                  ? data.macros.protein_g.toLocaleString() + 'g'
                  : data.macros.protein_g + 'g'}
              </span>
            </div>
            <div className="macro-item">
              <span className="macro-item__label">
                {t('whoTargets.macros.carbs', 'Carbs')}
              </span>
              <span className="macro-item__value">
                {typeof data.macros.carbs_g === 'number'
                  ? data.macros.carbs_g.toLocaleString() + 'g'
                  : data.macros.carbs_g + 'g'}
              </span>
            </div>
            <div className="macro-item">
              <span className="macro-item__label">
                {t('whoTargets.macros.fat', 'Fat')}
              </span>
              <span className="macro-item__value">
                {typeof data.macros.fat_g === 'number'
                  ? data.macros.fat_g.toLocaleString() + 'g'
                  : data.macros.fat_g + 'g'}
              </span>
            </div>
            <div className="macro-item">
              <span className="macro-item__label">
                {t('whoTargets.macros.fiber', 'Fiber')}
              </span>
              <span className="macro-item__value">
                {typeof data.macros.fiber_g === 'number'
                  ? data.macros.fiber_g.toLocaleString() + 'g'
                  : data.macros.fiber_g + 'g'}
              </span>
            </div>
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
            {data.water_ml.toLocaleString()}
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
                  <span className="micros-item__label">{micro}</span>
                  <span className="micros-item__value">
                    {value.toLocaleString()}
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
            <div className="activity-item">
              <span className="activity-item__label">
                {t('whoTargets.activity.moderateAerobic', 'Moderate Aerobic')}
              </span>
              <span className="activity-item__value">
                {data.activity_weekly.moderate_aerobic_min.toLocaleString()}
                <span className="activity-item__unit">
                  {t('whoTargets.activity.minutes', 'min/week')}
                </span>
              </span>
            </div>
            <div className="activity-item">
              <span className="activity-item__label">
                {t('whoTargets.activity.strength', 'Strength Training')}
              </span>
              <span className="activity-item__value">
                {data.activity_weekly.strength_sessions.toLocaleString()}
                <span className="activity-item__unit">
                  {t('whoTargets.activity.sessions', 'sessions/week')}
                </span>
              </span>
            </div>
            <div className="activity-item">
              <span className="activity-item__label">
                {t('whoTargets.activity.steps', 'Daily Steps')}
              </span>
              <span className="activity-item__value">
                {data.activity_weekly.steps_daily.toLocaleString()}
                <span className="activity-item__unit">
                  {t('whoTargets.activity.stepsUnit', 'steps')}
                </span>
              </span>
            </div>
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

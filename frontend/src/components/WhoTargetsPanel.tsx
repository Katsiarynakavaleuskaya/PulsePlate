import React from 'react';
import { useTranslation } from 'react-i18next';
import { clsx } from 'clsx';
import type { TargetsApiResponse } from '../api/premium/types';

interface WhoTargetsPanelProps {
  data: TargetsApiResponse | null;
  loading: boolean;
  error: string | null;
  onSaveAndContinue: () => void;
  className?: string;
}

export function WhoTargetsPanel({
  data,
  loading,
  error,
  onSaveAndContinue,
  className,
}: WhoTargetsPanelProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className={clsx('who-targets-panel', 'who-targets-panel--loading', className)}>
        <div className="who-targets-panel__header">
          <h2 className="who-targets-panel__title">
            {t('whoTargets.title', 'WHO Nutrition Targets')}
          </h2>
        </div>
        <div className="who-targets-panel__content">
          <div className="who-targets-panel__skeleton">
            <div className="skeleton skeleton--text skeleton--title" />
            <div className="skeleton skeleton--text skeleton--subtitle" />
            <div className="skeleton skeleton--card" />
            <div className="skeleton skeleton--card" />
            <div className="skeleton skeleton--card" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={clsx('who-targets-panel', 'who-targets-panel--error', className)}>
        <div className="who-targets-panel__header">
          <h2 className="who-targets-panel__title">
            {t('whoTargets.title', 'WHO Nutrition Targets')}
          </h2>
        </div>
        <div className="who-targets-panel__content">
          <div className="who-targets-panel__error">
            <div className="error-state">
              <div className="error-state__icon" aria-hidden="true">
                ⚠️
              </div>
              <h3 className="error-state__title">
                {t('whoTargets.error.title', 'Unable to Calculate Targets')}
              </h3>
              <p className="error-state__message">
                {error}
              </p>
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => window.location.reload()}
              >
                {t('whoTargets.error.retry', 'Try Again')}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className={clsx('who-targets-panel', 'who-targets-panel--empty', className)}>
        <div className="who-targets-panel__header">
          <h2 className="who-targets-panel__title">
            {t('whoTargets.title', 'WHO Nutrition Targets')}
          </h2>
        </div>
        <div className="who-targets-panel__content">
          <div className="empty-state">
            <div className="empty-state__icon" aria-hidden="true">
              📊
            </div>
            <h3 className="empty-state__title">
              {t('whoTargets.empty.title', 'No Targets Available')}
            </h3>
            <p className="empty-state__message">
              {t('whoTargets.empty.message', 'Please complete your profile to see personalized nutrition targets.')}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={clsx('who-targets-panel', 'who-targets-panel--loaded', className)}>
      <div className="who-targets-panel__header">
        <h2 className="who-targets-panel__title">
          {t('whoTargets.title', 'WHO Nutrition Targets')}
        </h2>
        <p className="who-targets-panel__subtitle">
          {t('whoTargets.subtitle', 'Personalized nutrition goals based on WHO guidelines')}
        </p>
      </div>

      <div className="who-targets-panel__content">
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
                  {data.macros.protein_g}g
                </span>
              </div>
              <div className="macro-item">
                <span className="macro-item__label">
                  {t('whoTargets.macros.carbs', 'Carbs')}
                </span>
                <span className="macro-item__value">
                  {data.macros.carbs_g}g
                </span>
              </div>
              <div className="macro-item">
                <span className="macro-item__label">
                  {t('whoTargets.macros.fat', 'Fat')}
                </span>
                <span className="macro-item__value">
                  {data.macros.fat_g}g
                </span>
              </div>
              <div className="macro-item">
                <span className="macro-item__label">
                  {t('whoTargets.macros.fiber', 'Fiber')}
                </span>
                <span className="macro-item__value">
                  {data.macros.fiber_g}g
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
                  {data.activity_weekly.moderate_aerobic_min}
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
                  {data.activity_weekly.strength_sessions}
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
                  <li key={index} className="warning-item">
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

        {/* CTA Button */}
        <div className="who-targets-panel__actions">
          <button
            type="button"
            className="btn btn--primary btn--large"
            onClick={onSaveAndContinue}
          >
            {t('whoTargets.cta.saveAndContinue', 'Save & Get Weekly Plan')}
          </button>
        </div>
      </div>
    </div>
  );
}

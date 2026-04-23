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

export default function NutritionSetupPage() {
  const { settings } = useSettings();
  const { t } = useTranslation();
  const [values, setValues] = useState<SetupFormValues | null>(null);
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
      <Stepper className="mb-6" currentStep={values ? 1 : 0} steps={[...setupSteps]} />
      {!values ? (
        <SetupForm onSubmit={setValues} />
      ) : (
        <ResultView values={values} onEdit={() => setValues(null)} />
      )}
    </div>
  );
}

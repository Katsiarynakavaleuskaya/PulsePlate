// RU: Контейнер страницы Nutrition Setup - анкета → результаты
// EN: Nutrition Setup page container - form → results

import { useState, useEffect } from 'react';
import SetupForm from './SetupForm';
import ResultView from './ResultView';
import type { SetupFormValues } from './schema';
import { isValidSetupFormValues } from './schema';
import { useSettings } from '../../lib/settings';
import { Stepper } from '../../components/ui';

const setupSteps = [
  { id: 'profile', label: 'Profile', description: 'Capture your nutrition inputs' },
  { id: 'results', label: 'Results', description: 'Review macros and targets' },
] as const;

export default function NutritionSetupPage() {
  const { settings } = useSettings();
  const [values, setValues] = useState<SetupFormValues | null>(null);

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

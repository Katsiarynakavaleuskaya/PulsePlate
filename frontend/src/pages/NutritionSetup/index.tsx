// RU: Контейнер страницы Nutrition Setup - анкета → результаты
// EN: Nutrition Setup page container - form → results

import { useState, useEffect } from 'react';
import SetupForm from './SetupForm';
import ResultView from './ResultView';
import type { SetupFormValues } from './schema';
import { setupSchema } from './schema';
import { useSettings } from '../../lib/settings';

// Runtime type guard for SetupFormValues
function isValidSetupFormValues(data: unknown): data is SetupFormValues {
  const result = setupSchema.safeParse(data);
  return result.success;
}

export default function NutritionSetupPage() {
  const { settings } = useSettings();
  const [values, setValues] = useState<SetupFormValues | null>(null);

  // Initialize values from saved settings on mount
  useEffect(() => {
    if (isValidSetupFormValues(settings.setup)) {
      setValues(settings.setup);
    }
  }, [settings.setup]);

  return (
    <div className="max-w-4xl mx-auto p-4 pb-20">
      {!values ? (
        <SetupForm onSubmit={setValues} />
      ) : (
        <ResultView values={values} onEdit={() => setValues(null)} />
      )}
    </div>
  );
}

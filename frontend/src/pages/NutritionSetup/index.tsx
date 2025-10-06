// RU: Контейнер страницы Nutrition Setup - анкета → результаты
// EN: Nutrition Setup page container - form → results

import { useState } from 'react';
import SetupForm from './SetupForm';
import ResultView from './ResultView';
import type { SetupFormValues } from './schema';

export default function NutritionSetupPage() {
  const [values, setValues] = useState<SetupFormValues | null>(null);

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

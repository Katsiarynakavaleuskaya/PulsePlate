// RU: Компонент отображения результатов расчета - тарелка + макро/микро/вода
// EN: Results display component - plate + macro/micro/water

import { useSetupCalc, useTargets } from './hooks';
import PlateChart from './PlateChart';
import MacroCards from './MacroCards';
import WaterCard from './WaterCard';
import MicrosGrid from './MicrosGrid';
import type { SetupFormValues } from './schema';

interface ResultViewProps {
  values: SetupFormValues;
  onEdit: () => void;
}

export default function ResultView({ values, onEdit }: ResultViewProps) {
  const { bmrData, plateData, loading, error } = useSetupCalc(values);
  const { data: targetsData, loading: targetsLoading, error: targetsError } = useTargets('ru');

  if (loading || targetsLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted">Рассчитываем вашу персональную тарелку...</p>
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
        <h2 className="text-xl font-semibold text-text mb-2">Ошибка расчета</h2>
        <p className="text-muted mb-6">
          {error || targetsError || 'Не удалось загрузить данные. Проверьте подключение к интернету.'}
        </p>
        <div className="flex gap-4 justify-center">
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-3 bg-primary text-navy rounded-xl font-medium hover:bg-primary/90 transition-colors"
          >
            Попробовать снова
          </button>
          <button
            onClick={onEdit}
            className="px-6 py-3 bg-muted/20 text-text rounded-xl font-medium hover:bg-muted/30 transition-colors"
          >
            Изменить данные
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-text">Ваша персональная тарелка</h1>
            <p className="text-muted mt-1">Расчет основан на ваших параметрах</p>
          </div>
          <button
            onClick={onEdit}
            className="px-4 py-2 text-primary hover:text-primary/80 underline font-medium transition-colors"
          >
            Изменить анкету
          </button>
        </div>

        {/* BMR/TDEE Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-navy/5 rounded-xl">
          <div className="text-center">
            <div className="text-2xl font-bold text-primary">{Math.round(bmrData.bmr)}</div>
            <div className="text-sm text-muted">BMR (ккал)</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-primary">{Math.round(bmrData.tdee)}</div>
            <div className="text-sm text-muted">TDEE (ккал)</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-primary">{Math.round(plateData.plate.kcal)}</div>
            <div className="text-sm text-muted">Цель (ккал)</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-primary">{bmrData.method}</div>
            <div className="text-sm text-muted">Метод</div>
          </div>
        </div>
      </div>

      {/* Plate Chart and Macros */}
      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-1">
          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-text mb-4 text-center">Распределение макронутриентов</h2>
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

          <WaterCard liters={plateData.water_l} />
        </div>
      </div>

      {/* Micros */}
      {targetsData && (
        <div className="bg-white rounded-2xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-text mb-4">Цели по микроэлементам</h2>
          <p className="text-muted mb-6 text-sm">
            Рекомендуемые суточные нормы витаминов и минералов для вашего возраста и пола
          </p>
          <MicrosGrid items={targetsData.micros} />
        </div>
      )}
    </div>
  );
}

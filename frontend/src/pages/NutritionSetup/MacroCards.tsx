// RU: Карточки с информацией о макронутриентах и калориях
// EN: Cards displaying macronutrient and calorie information

interface MacroCardsProps {
  kcal: number;
  carbsG: number;
  proteinG: number;
  fatG: number;
  fiberG: number;
  bmr: number;
  tdee: number;
}

export default function MacroCards({
  kcal,
  carbsG,
  proteinG,
  fatG,
  fiberG,
  bmr,
  tdee,
}: MacroCardsProps) {
  const Item = ({ label, value, unit }: { label: string; value: number; unit: string }) => (
    <div className="bg-white rounded-xl p-4 border border-muted/30 hover:shadow-sm transition-shadow">
      <div className="text-sm text-muted mb-1">{label}</div>
      <div className="text-xl font-bold text-text">
        {typeof value === 'number' && !isNaN(value) ? Math.round(value) : '-'}
      </div>
      <div className="text-xs text-muted">{unit}</div>
    </div>
  );

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-text mb-4">Макронутриенты и калории</h3>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {typeof kcal === 'number' && !isNaN(kcal) && (
          <Item label="Калории (цель)" value={kcal} unit="ккал/день" />
        )}
        {typeof carbsG === 'number' && !isNaN(carbsG) && (
          <Item label="Углеводы" value={carbsG} unit="г/день" />
        )}
        {typeof proteinG === 'number' && !isNaN(proteinG) && (
          <Item label="Белки" value={proteinG} unit="г/день" />
        )}
        {typeof fatG === 'number' && !isNaN(fatG) && (
          <Item label="Жиры" value={fatG} unit="г/день" />
        )}
        {typeof fiberG === 'number' && !isNaN(fiberG) && (
          <Item label="Клетчатка" value={fiberG} unit="г/день" />
        )}
        {typeof bmr === 'number' && !isNaN(bmr) && (
          <Item label="BMR" value={bmr} unit="ккал/день" />
        )}
        {typeof tdee === 'number' && !isNaN(tdee) && (
          <Item label="TDEE" value={tdee} unit="ккал/день" />
        )}
      </div>

      <div className="mt-4 p-3 bg-navy/5 rounded-lg">
        <p className="text-xs text-muted">
          <strong>BMR</strong> - базовый метаболизм (калории для поддержания жизни)<br/>
          <strong>TDEE</strong> - общий расход энергии с учетом активности
        </p>
      </div>
    </div>
  );
}

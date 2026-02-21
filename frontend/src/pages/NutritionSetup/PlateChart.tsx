// RU: Простая SVG-диаграмма распределения макронутриентов в тарелке
// EN: Simple SVG chart showing macronutrient distribution in the plate

import { useTranslation } from 'react-i18next';

interface PlateChartProps {
  carbsPct: number;
  proteinPct: number;
  fatPct: number;
}

export default function PlateChart({ carbsPct, proteinPct, fatPct }: PlateChartProps) {
  const { t } = useTranslation();

  // Ensure all values are numbers (defensive programming)
  const safeCarbsPct = Number(carbsPct) || 0;
  const safeProteinPct = Number(proteinPct) || 0;
  const safeFatPct = Number(fatPct) || 0;

  // Validate percentages sum to 100% (allow small floating-point tolerance)
  const total = safeCarbsPct + safeProteinPct + safeFatPct;
  if (Math.abs(total - 100) > 0.1) {
    console.warn(`Plate percentages sum to ${total.toFixed(1)}%, expected 100%`);
  }

  // Calculate stroke dash arrays for the circular segments
  const radius = 45;
  const circumference = 2 * Math.PI * radius;

  const carbsAngle = (safeCarbsPct / 100) * 360;
  const proteinAngle = (safeProteinPct / 100) * 360;
  const fatAngle = (safeFatPct / 100) * 360;

  const carbsDash = (carbsAngle / 360) * circumference;
  const proteinDash = (proteinAngle / 360) * circumference;
  const fatDash = (fatAngle / 360) * circumference;

  return (
    <div className="flex flex-col items-center">
      <svg
        width="120"
        height="120"
        viewBox="0 0 110 110"
        className="drop-shadow-sm"
        role="img"
        aria-label={t('nutrition.plate.ariaLabel', {
          carbs: Math.round(safeCarbsPct),
          protein: Math.round(safeProteinPct),
          fat: Math.round(safeFatPct),
        })}
      >
        {/* Background circle */}
        <circle
          cx="55"
          cy="55"
          r={radius}
          fill="none"
          stroke="var(--color-gray-100)"
          strokeWidth="8"
        />

        {/* Carbs segment (blue) */}
        <circle
          cx="55"
          cy="55"
          r={radius}
          fill="none"
          stroke="var(--pp-blue)"
          strokeWidth="8"
          strokeDasharray={`${carbsDash} ${circumference}`}
          strokeDashoffset={circumference * 0.25}
          transform="rotate(-90 55 55)"
        />

        {/* Protein segment (green) */}
        <circle
          cx="55"
          cy="55"
          r={radius}
          fill="none"
          stroke="var(--pp-green)"
          strokeWidth="8"
          strokeDasharray={`${proteinDash} ${circumference}`}
          strokeDashoffset={circumference * 0.25 + carbsDash}
          transform="rotate(-90 55 55)"
        />

        {/* Fat segment (red) */}
        <circle
          cx="55"
          cy="55"
          r={radius}
          fill="none"
          stroke="var(--pp-red)"
          strokeWidth="8"
          strokeDasharray={`${fatDash} ${circumference}`}
          strokeDashoffset={circumference * 0.25 + carbsDash + proteinDash}
          transform="rotate(-90 55 55)"
        />
      </svg>

      {/* Legend */}
      <div className="mt-4 space-y-2 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: 'var(--pp-blue)' }}></div>
          <span className="text-text">{t('nutrition.macros.carbs')}: {Math.round(safeCarbsPct)}%</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: 'var(--pp-green)' }}></div>
          <span className="text-text">{t('nutrition.macros.protein')}: {Math.round(safeProteinPct)}%</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: 'var(--pp-red)' }}></div>
          <span className="text-text">{t('nutrition.macros.fat')}: {Math.round(safeFatPct)}%</span>
        </div>
      </div>
    </div>
  );
}

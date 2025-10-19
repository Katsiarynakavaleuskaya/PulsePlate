// RU: Карточки с информацией о макронутриентах и калориях
// EN: Cards displaying macronutrient and calorie information

import { useTranslation } from 'react-i18next';

export interface MacroCardsProps {
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
  const { t } = useTranslation();

  const Item = ({ label, value, unit }: { label: string; value: number; unit: string }) => (
    <div className="bg-white rounded-xl p-4 border border-muted/30 hover:shadow-sm transition-shadow">
      <div className="text-sm text-muted mb-1">{label}</div>
      <div className="text-xl font-bold text-text">
        {Number.isFinite(value) ? Math.round(value) : '-'}
      </div>
      <div className="text-xs text-muted">{unit}</div>
    </div>
  );

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-4">
        <Item
          label={t('nutrition.macros.caloriesLabel')}
          value={kcal}
          unit={t('nutrition.units.kcalPerDay')}
        />
        <Item
          label={t('nutrition.macros.carbsLabel')}
          value={carbsG}
          unit={t('nutrition.units.gPerDay')}
        />
        <Item
          label={t('nutrition.macros.proteinLabel')}
          value={proteinG}
          unit={t('nutrition.units.gPerDay')}
        />
        <Item
          label={t('nutrition.macros.fatLabel')}
          value={fatG}
          unit={t('nutrition.units.gPerDay')}
        />
        <Item
          label={t('nutrition.macros.fiberLabel')}
          value={fiberG}
          unit={t('nutrition.units.gPerDay')}
        />
        <Item
          label={t('nutrition.macros.bmrLabel')}
          value={bmr}
          unit={t('nutrition.units.kcalPerDay')}
        />
        <Item
          label={t('nutrition.macros.tdeeLabel')}
          value={tdee}
          unit={t('nutrition.units.kcalPerDay')}
        />
      </div>

      <div className="mt-4 p-3 bg-navy/5 rounded-lg">
        <p className="text-xs text-muted">
          <strong>{t('nutrition.macros.bmrLabel')}</strong> - {t('nutrition.macros.bmrDescription')}
          <br />
          <strong>{t('nutrition.macros.tdeeLabel')}</strong> -{' '}
          {t('nutrition.macros.tdeeDescription')}
        </p>
      </div>
    </div>
  );
}

// RU: Карточки с информацией о макронутриентах и калориях
// EN: Cards displaying macronutrient and calorie information

import { useTranslation } from "react-i18next";
import { StatsCard } from '../../components/ui';

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

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-4">
        <StatsCard align="center" label={t('nutrition.macros.caloriesLabel')} unit={t('nutrition.units.kcalPerDay')} value={Number.isFinite(kcal) ? Math.round(kcal) : '-'} />
        <StatsCard align="center" label={t('nutrition.macros.carbsLabel')} unit={t('nutrition.units.gPerDay')} value={Number.isFinite(carbsG) ? Math.round(carbsG) : '-'} />
        <StatsCard align="center" label={t('nutrition.macros.proteinLabel')} unit={t('nutrition.units.gPerDay')} value={Number.isFinite(proteinG) ? Math.round(proteinG) : '-'} />
        <StatsCard align="center" label={t('nutrition.macros.fatLabel')} unit={t('nutrition.units.gPerDay')} value={Number.isFinite(fatG) ? Math.round(fatG) : '-'} />
        <StatsCard align="center" label={t('nutrition.macros.fiberLabel')} unit={t('nutrition.units.gPerDay')} value={Number.isFinite(fiberG) ? Math.round(fiberG) : '-'} />
        <StatsCard align="center" label={t('nutrition.macros.bmrLabel')} unit={t('nutrition.units.kcalPerDay')} value={Number.isFinite(bmr) ? Math.round(bmr) : '-'} />
        <StatsCard align="center" label={t('nutrition.macros.tdeeLabel')} unit={t('nutrition.units.kcalPerDay')} value={Number.isFinite(tdee) ? Math.round(tdee) : '-'} />
      </div>

      <div className="mt-4 p-3 bg-navy/5 rounded-lg">
        <p className="text-xs text-muted">
          <strong>{t('nutrition.macros.bmrLabel')}</strong> - {t('nutrition.macros.bmrDescription')}<br/>
          <strong>{t('nutrition.macros.tdeeLabel')}</strong> - {t('nutrition.macros.tdeeDescription')}
        </p>
      </div>
    </div>
  );
}

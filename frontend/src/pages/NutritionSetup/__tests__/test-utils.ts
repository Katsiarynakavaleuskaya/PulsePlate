import type { SetupFormValues } from "../schema";

export const createMockI18n = () => () => ({
  i18n: { language: "en" },
  t: (key: string) => {
    const translations: Record<string, string> = {
      "nutrition.macros.title": "Макронутриенты",
      "nutrition.macros.caloriesLabel": "Калории (цель)",
      "nutrition.macros.carbsLabel": "Углеводы",
      "nutrition.macros.proteinLabel": "Белки",
      "nutrition.macros.fatLabel": "Жиры",
      "nutrition.macros.fiberLabel": "Клетчатка",
      "nutrition.macros.bmrLabel": "BMR",
      "nutrition.macros.tdeeLabel": "TDEE",
      "nutrition.macros.bmrDescription": "базовый метаболизм",
      "nutrition.macros.tdeeDescription": "общий расход калорий",
      "nutrition.units.kcalPerDay": "ккал/день",
      "nutrition.units.gPerDay": "г/день",
      "nutrition.loadingPlate": "Рассчитываем вашу персональную тарелку...",
      "common.retrying": "Повторная попытка...",
      "common.tryAgain": "Попробовать снова",
    };
    return translations[key] || key;
  },
});

export const mockValues: SetupFormValues = {
  sex: "female",
  age: 30,
  height_cm: 170,
  weight_kg: 65,
  activity: "moderate",
  goal: "maintain",
  diet_flags: [],
};

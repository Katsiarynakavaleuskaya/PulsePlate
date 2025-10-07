// RU: Хуки для работы с реальными API расчётов Nutrition Setup
// EN: Hooks interacting with live Nutrition Setup APIs

import { useState, useEffect, useRef } from 'react';
import { getBmr, getPlate, getTargets } from '../../api/premium';
import type {
  SetupFormValues,
  EnrichedBmrResponse,
  PlateResponse,
  TargetsResponse,
} from './schema';
import type { PlateApiResponse, BmrApiResponse, TargetsApiResponse } from '../../api/premium';

const ACTIVITY_MAP: Record<SetupFormValues['activity'], 'sedentary' | 'light' | 'moderate' | 'active' | 'very_active'> = {
  sedentary: 'sedentary',
  light: 'light',
  moderate: 'moderate',
  active: 'active',
  athlete: 'very_active',
};

const GOAL_MAP: Record<SetupFormValues['goal'], 'loss' | 'maintain' | 'gain'> = {
  lose: 'loss',
  maintain: 'maintain',
  gain: 'gain',
};

const GOAL_DEFAULTS: Record<'loss' | 'maintain' | 'gain', { deficit_pct?: number | null; surplus_pct?: number | null }> =
  {
    loss: { deficit_pct: 15 },
    maintain: {},
    gain: { surplus_pct: 10 },
  };

const DEFAULT_ACTIVITY_MULTIPLIERS: Record<keyof typeof ACTIVITY_MAP, number> = {
  sedentary: 1.2,
  light: 1.375,
  moderate: 1.55,
  active: 1.725,
  athlete: 1.9,
};

const SUPPORTED_DIET_FLAGS = new Set(['VEG', 'GF', 'DAIRY_FREE', 'LOW_COST']);

const MICRO_CONFIG: Record<
  string,
  {
    id: string;
    names: Record<'ru' | 'en' | 'es', string>;
    units: Record<'ru' | 'en' | 'es', string>;
  }
> = {
  iron_mg: {
    id: 'iron',
    names: { ru: 'Железо', en: 'Iron', es: 'Hierro' },
    units: { ru: 'мг', en: 'mg', es: 'mg' },
  },
  calcium_mg: {
    id: 'calcium',
    names: { ru: 'Кальций', en: 'Calcium', es: 'Calcio' },
    units: { ru: 'мг', en: 'mg', es: 'mg' },
  },
  potassium_mg: {
    id: 'potassium',
    names: { ru: 'Калий', en: 'Potassium', es: 'Potasio' },
    units: { ru: 'мг', en: 'mg', es: 'mg' },
  },
  magnesium_mg: {
    id: 'magnesium',
    names: { ru: 'Магний', en: 'Magnesium', es: 'Magnesio' },
    units: { ru: 'мг', en: 'mg', es: 'mg' },
  },
  zinc_mg: {
    id: 'zinc',
    names: { ru: 'Цинк', en: 'Zinc', es: 'Zinc' },
    units: { ru: 'мг', en: 'mg', es: 'mg' },
  },
  iodine_ug: {
    id: 'iodine',
    names: { ru: 'Йод', en: 'Iodine', es: 'Yodo' },
    units: { ru: 'мкг', en: 'mcg', es: 'mcg' },
  },
  vitamin_d_iu: {
    id: 'vitamin_d',
    names: { ru: 'Витамин D', en: 'Vitamin D', es: 'Vitamina D' },
    units: { ru: 'МЕ', en: 'IU', es: 'UI' },
  },
  b12_ug: {
    id: 'vitamin_b12',
    names: { ru: 'Витамин B12', en: 'Vitamin B12', es: 'Vitamina B12' },
    units: { ru: 'мкг', en: 'mcg', es: 'mcg' },
  },
  folate_ug: {
    id: 'folate',
    names: { ru: 'Фолат', en: 'Folate', es: 'Folato' },
    units: { ru: 'мкг', en: 'mcg', es: 'mcg' },
  },
  vitamin_c_mg: {
    id: 'vitamin_c',
    names: { ru: 'Витамин C', en: 'Vitamin C', es: 'Vitamina C' },
    units: { ru: 'мг', en: 'mg', es: 'mg' },
  },
};

const safeNumber = (value: unknown): number | null =>
  typeof value === 'number' && !Number.isNaN(value) ? value : null;

const mapActivityToApi = (activity: SetupFormValues['activity']) => ACTIVITY_MAP[activity] ?? 'moderate';

const mapGoalToApi = (goal: SetupFormValues['goal']) => {
  const mapped = GOAL_MAP[goal] ?? 'maintain';
  return {
    goal: mapped,
    ...GOAL_DEFAULTS[mapped],
  };
};

const filterDietFlags = (flags: SetupFormValues['diet_flags']) => {
  const filtered = flags.filter(flag => SUPPORTED_DIET_FLAGS.has(flag));
  return filtered.length ? filtered : null;
};

const determineLifeStage = (age: number): 'child' | 'teen' | 'adult' | 'elderly' => {
  if (age <= 12) return 'child';
  if (age <= 17) return 'teen';
  if (age >= 65) return 'elderly';
  return 'adult';
};

const normalizeBmrResponse = (
  response: BmrApiResponse,
  uiActivity: SetupFormValues['activity'],
  apiActivity: ReturnType<typeof mapActivityToApi>,
): EnrichedBmrResponse => {
  const mifflin = safeNumber(response.bmr?.mifflin);
  const firstBmr = Object.values(response.bmr ?? {}).find(value => safeNumber(value) !== null);
  const bmr = Math.round(mifflin ?? (safeNumber(firstBmr) ?? 0));

  const method =
    response.formulas_used?.[0] ??
    (mifflin !== null ? 'Mifflin-St Jeor' : 'BMR');

  const tdeeFromApi = safeNumber(response.tdee?.[apiActivity]);
  const fallbackMultiplier = DEFAULT_ACTIVITY_MULTIPLIERS[uiActivity] ?? DEFAULT_ACTIVITY_MULTIPLIERS.moderate;
  const tdee =
    Math.round(
      tdeeFromApi ??
        (safeNumber(Object.values(response.tdee ?? {})[0]) ??
          bmr * fallbackMultiplier),
    ) || Math.round(bmr * fallbackMultiplier);

  return {
    bmr,
    tdee,
    method,
  };
};

const normalizePlateResponse = (response: PlateApiResponse): PlateResponse => {
  const proteinG = safeNumber(response.macros?.protein_g) ?? safeNumber(response.macros?.protein) ?? null;
  const fatG = safeNumber(response.macros?.fat_g) ?? safeNumber(response.macros?.fat) ?? null;
  const carbsG = safeNumber(response.macros?.carbs_g) ?? safeNumber(response.macros?.carbs) ?? null;
  const fiberG = safeNumber(response.macros?.fiber_g) ?? 0;

  if (proteinG === null || fatG === null || carbsG === null) {
    throw new Error('Plate response missing macronutrient data');
  }

  const macroKcal = {
    protein: proteinG * 4,
    fat: fatG * 9,
    carbs: carbsG * 4,
  };

  const totalKcal =
    safeNumber(response.kcal) ??
    (macroKcal.protein + macroKcal.fat + macroKcal.carbs);

  const toPct = (macro: number) => {
    if (totalKcal <= 0) return 0;
    return (macro / totalKcal) * 100;
  };

  return {
    plate: {
      carbs_pct: toPct(macroKcal.carbs),
      protein_pct: toPct(macroKcal.protein),
      fat_pct: toPct(macroKcal.fat),
      kcal: Math.round(totalKcal),
    },
    macros: {
      carbs_g: carbsG,
      protein_g: proteinG,
      fat_g: fatG,
      fiber_g: fiberG ?? 0,
    },
    water_l: null,
  };
};

const defaultMicronutrientMeta = (key: string) => {
  const baseId = key.replace(/_(mg|mcg|ug|iu)$/i, '');
  const capitalized = baseId
    .split('_')
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');

  let unit: Record<'ru' | 'en' | 'es', string> = { ru: '', en: '', es: '' };
  if (/_mg$/i.test(key)) {
    unit = { ru: 'мг', en: 'mg', es: 'mg' };
  } else if (/_ug$/i.test(key) || /_(mcg)$/i.test(key)) {
    unit = { ru: 'мкг', en: 'mcg', es: 'mcg' };
  } else if (/_iu$/i.test(key)) {
    unit = { ru: 'МЕ', en: 'IU', es: 'UI' };
  }

  return {
    id: baseId,
    names: { ru: capitalized, en: capitalized, es: capitalized },
    units: unit,
  };
};

const convertPriorityMicros = (
  priorityMicros: Record<string, number>,
  lang: 'ru' | 'en' | 'es',
): TargetsResponse['micros'] =>
  Object.entries(priorityMicros).map(([key, value]) => {
    const meta = MICRO_CONFIG[key] ?? defaultMicronutrientMeta(key);
    return {
      id: meta.id,
      name: meta.names[lang] ?? meta.names.en,
      unit: meta.units[lang] ?? meta.units.en ?? '',
      target: value,
    };
  });

const normalizeTargetsResponse = (
  response: TargetsApiResponse,
  lang: 'ru' | 'en' | 'es',
): TargetsResponse => {
  const micros = convertPriorityMicros(response.priority_micros ?? {}, lang);
  const waterMl = safeNumber(response.water_ml);

  return {
    micros,
    water_l: waterMl !== null ? waterMl / 1000 : null,
  };
};

export function useSetupCalc(values: SetupFormValues | null) {
  const [bmrData, setBmrData] = useState<EnrichedBmrResponse | null>(null);
  const [plateData, setPlateData] = useState<PlateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const enabled = !!values;

  useEffect(() => {
    if (!enabled || !values) {
      setBmrData(null);
      setPlateData(null);
      setError(null);
      setLoading(false);
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      setBmrData(null);
      setPlateData(null);

      try {
        const apiActivity = mapActivityToApi(values.activity);
        const goalPayload = mapGoalToApi(values.goal);
        const dietFlags = filterDietFlags(values.diet_flags);

        const bmrPromise = getBmr(
          {
            sex: values.sex,
            age: values.age,
            height_cm: values.height_cm,
            weight_kg: values.weight_kg,
            activity: apiActivity,
            lang: 'ru',
          },
          { signal: abortController.signal },
        );

        const platePromise = getPlate(
          {
            sex: values.sex,
            age: values.age,
            height_cm: values.height_cm,
            weight_kg: values.weight_kg,
            activity: apiActivity,
            goal: goalPayload.goal,
            deficit_pct: goalPayload.deficit_pct ?? null,
            surplus_pct: goalPayload.surplus_pct ?? null,
            diet_flags: dietFlags,
          },
          { signal: abortController.signal },
        );

        const [bmrResult, plateResult] = await Promise.all([bmrPromise, platePromise]);

        if (!bmrResult) {
          throw new Error('BMR API returned empty response');
        }

        if (!plateResult) {
          throw new Error('Plate API returned empty response');
        }

        setBmrData(normalizeBmrResponse(bmrResult, values.activity, apiActivity));
        setPlateData(normalizePlateResponse(plateResult));
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          return;
        }
        console.error('Nutrition setup calculation error:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    return () => {
      abortController.abort();
    };
  }, [enabled, values]);

  return {
    bmrData,
    plateData,
    loading,
    error,
    enabled,
  };
}

export function useTargets(values: SetupFormValues | null, lang: 'ru' | 'en' | 'es' = 'ru') {
  const [data, setData] = useState<TargetsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!values) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    const fetchTargets = async () => {
      setLoading(true);
      setError(null);

      try {
        const apiActivity = mapActivityToApi(values.activity);
        const goalPayload = mapGoalToApi(values.goal);
        const dietFlags = filterDietFlags(values.diet_flags);

        const response = await getTargets(
          {
            sex: values.sex,
            age: values.age,
            height_cm: values.height_cm,
            weight_kg: values.weight_kg,
            activity: apiActivity,
            goal: goalPayload.goal,
            deficit_pct: goalPayload.deficit_pct ?? null,
            surplus_pct: goalPayload.surplus_pct ?? null,
            diet_flags: dietFlags,
            life_stage: determineLifeStage(values.age),
            lang,
          },
          { signal: abortController.signal },
        );

        setData(normalizeTargetsResponse(response, lang));
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          return;
        }
        console.error('Targets fetch error:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchTargets();

    return () => {
      abortController.abort();
    };
  }, [values, lang]);

  return {
    data,
    loading,
    error,
  };
}

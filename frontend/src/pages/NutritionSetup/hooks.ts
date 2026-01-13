// RU: Хуки для работы с реальными API расчётов Nutrition Setup
// EN: Hooks interacting with live Nutrition Setup APIs

import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { getBmr, getPlate, getTargets } from '../../api/premium';
import type {
  SetupFormValues,
  NormalizedBmrData,
  NormalizedBmrMethod,
  PlateResponse,
  TargetsResponse,
} from './schema';
import { validDietFlags } from './schema';
import type { PlateResponse as ApiPlateResponse, BmrApiResponse, TargetsApiResponse, SupportedPremiumLang } from '../../api/premium';

const SUPPORTED_LANGS: SupportedPremiumLang[] = ['ru', 'en', 'es'];

type SetupSupportedLang = SupportedPremiumLang;

// Shared auth error handler for observability.
// Intentionally DOES NOT call clearApiKey() or redirect:
// when no custom handler is provided, the API client's fallback
// will clear the stored key and redirect to /enter-key on 401/403.
const handleAuthErrorShared = (code: 401 | 403, _helpers: { clearApiKey: () => void }) => {
  console.warn(`[auth] Premium API error: ${code}`);
};

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

const KNOWN_BMR_METHODS: ReadonlySet<NormalizedBmrMethod> = new Set([
  'Mifflin-St Jeor',
  'Harris-Benedict',
  'Katch-McArdle',
  'BMR',
]);

const DEFAULT_ACTIVITY_MULTIPLIERS: Record<keyof typeof ACTIVITY_MAP, number> = {
  sedentary: 1.2,
  light: 1.375,
  moderate: 1.55,
  active: 1.725,
  athlete: 1.9,
};

/**
 * Diet flags handling
 * - UI allows a broad set (`validDietFlags`)
 * - API (OpenAPI) currently supports a narrower enum: VEG | GF | DAIRY_FREE | LOW_COST
 * - Normalize and filter before sending to API to satisfy Typescript and backend contract
 */
const UI_DIET_FLAGS = new Set(validDietFlags);
const BACKEND_DIET_FLAGS = new Set(["VEG", "GF", "DAIRY_FREE", "LOW_COST"] as const);

const normalizeDietFlagsForApi = (flags: ReadonlyArray<string>): Array<"VEG" | "GF" | "DAIRY_FREE" | "LOW_COST"> => {
  const mapped: Array<string> = [];
  for (const flag of flags) {
    if (!UI_DIET_FLAGS.has(flag as any)) continue;
    switch (flag) {
      case "VEGAN":
        mapped.push("VEG");
        break;
      case "KETO":
      case "LOW_CARB":
      case "HIGH_PROTEIN":
      case "PALEO":
      case "MEDITERRANEAN":
        // Not sent to backend; handled locally in UI/macros if needed
        break;
      case "VEG":
      case "GF":
      case "DAIRY_FREE":
      case "LOW_COST":
        mapped.push(flag);
        break;
      default:
        break;
    }
  }
  const unique = Array.from(new Set(mapped)).filter((f): f is "VEG" | "GF" | "DAIRY_FREE" | "LOW_COST" =>
    BACKEND_DIET_FLAGS.has(f as any),
  );
  return unique;
};

const FALLBACK_LANG: SetupSupportedLang = 'en';

const normalizeLang = (value?: string): SetupSupportedLang | undefined => {
  if (!value) {
    return undefined;
  }

  const root = value.toLowerCase().slice(0, 2);
  if (root === 'ru') return 'ru';
  if (root === 'es') return 'es';
  if (root === 'en') return 'en';
  return undefined;
};

export const resolveSetupLang = (
  explicit?: SetupSupportedLang,
  i18nLang?: string,
  browserLang?: string,
): SetupSupportedLang => {
  if (explicit && SUPPORTED_LANGS.includes(explicit)) {
    return explicit;
  }

  const normalizedFromI18n = normalizeLang(i18nLang);
  if (normalizedFromI18n) {
    return normalizedFromI18n;
  }

  const normalizedFromBrowser = normalizeLang(browserLang);
  if (normalizedFromBrowser) {
    return normalizedFromBrowser;
  }

  return FALLBACK_LANG;
};

export const MICRO_CONFIG: Record<
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
  const normalized = normalizeDietFlagsForApi(flags);
  return normalized.length ? normalized : null;
};

const determineLifeStage = (age: number): 'child' | 'teen' | 'adult' | 'elderly' => {
  if (age <= 12) return 'child';
  if (age <= 17) return 'teen';
  if (age >= 65) return 'elderly';
  return 'adult';
};

const collectNumericValues = (source: unknown): number[] => {
  if (typeof source === 'number') {
    const value = safeNumber(source);
    return value === null ? [] : [value];
  }
  if (source && typeof source === 'object') {
    const values: number[] = [];
    for (const entry of Object.values(source as Record<string, unknown>)) {
      const numeric = safeNumber(entry);
      if (numeric !== null) {
        values.push(numeric);
      }
    }
    return values;
  }
  return [];
};

const normalizeBmrResponse = (
  response: BmrApiResponse,
  uiActivity: SetupFormValues['activity'],
): NormalizedBmrData => {

  const bmrValues = collectNumericValues(response.bmr);
  const mifflin = safeNumber(response.bmr.mifflin);
  const rawBmr = mifflin ?? bmrValues[0] ?? null;
  const bmr = Math.round(rawBmr ?? 0);

  const tdeeValues = collectNumericValues(response.tdee);
  const primaryTdee = safeNumber(response.tdee.mifflin);
  const rawTdee = primaryTdee ?? tdeeValues[0] ?? null;
  const fallbackMultiplier = DEFAULT_ACTIVITY_MULTIPLIERS[uiActivity] ?? DEFAULT_ACTIVITY_MULTIPLIERS.moderate;
  const tdee = Math.round(rawTdee ?? bmr * fallbackMultiplier);

  const formulasUsed = Array.isArray(response.formulas_used) ? response.formulas_used : [];
  const responseMethod = typeof response.method === 'string' ? response.method : null;

  const method: NormalizedBmrMethod = (() => {
    const methodFromFormulas = formulasUsed.find(method => typeof method === 'string') as string | undefined;
    if (methodFromFormulas && KNOWN_BMR_METHODS.has(methodFromFormulas as NormalizedBmrMethod)) {
      return methodFromFormulas as NormalizedBmrMethod;
    }
    if (responseMethod && KNOWN_BMR_METHODS.has(responseMethod as NormalizedBmrMethod)) {
      return responseMethod as NormalizedBmrMethod;
    }
    if (rawBmr !== null) {
      return mifflin !== null ? 'Mifflin-St Jeor' : 'BMR';
    }
    return 'stub';
  })();

  return {
    bmr,
    tdee,
    method,
  };
};

const normalizePlateResponse = (response: ApiPlateResponse): PlateResponse => {
  const macros = response.macros ?? {};

  const proteinG = safeNumber((macros as Record<string, unknown>)?.protein_g ?? (macros as Record<string, unknown>)?.protein) ?? null;
  const fatG     = safeNumber((macros as Record<string, unknown>)?.fat_g     ?? (macros as Record<string, unknown>)?.fat)     ?? null;
  const carbsG   = safeNumber((macros as Record<string, unknown>)?.carbs_g   ?? (macros as Record<string, unknown>)?.carbs)   ?? null;
  const fiberG   = safeNumber((macros as Record<string, unknown>)?.fiber_g   ?? (macros as Record<string, unknown>)?.fiber)   ?? null;

  if (proteinG === null || fatG === null || carbsG === null || fiberG === null) {
    console.error('Plate response missing macronutrient data', { macros: response.macros });
    return {
      plate: {
        carbs_pct: 0,
        protein_pct: 0,
        fat_pct: 0,
        kcal:      0,
      },
      macros: {
        carbs_g:  0,
        protein_g:0,
        fat_g:    0,
        fiber_g:  0,
      },
      water_l: null,
    };
  }

  const macroKcal = {
    protein: proteinG * 4,
    fat:     fatG * 9,
    carbs:   carbsG * 4,
  };

  const totalKcal =
    safeNumber(response.kcal) ??
    (macroKcal.protein + macroKcal.fat + macroKcal.carbs);

  const toPct = (macro: number) => {
    if (totalKcal <= 0) {
      console.warn(
        'Data quality issue: normalizePlateResponse returning 0% for macronutrients due to zero/negative total calories',
        { totalKcal, rawKcal: response.kcal, rawMacros: response.macros },
      );
      return 0;
    }
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
      fiber_g: fiberG,
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

export function useSetupCalc(values: SetupFormValues | null, lang?: SetupSupportedLang, retryKey?: number) {
  const { i18n } = useTranslation();
  const [bmrData, setBmrData] = useState<NormalizedBmrData | null>(null);
  const [plateData, setPlateData] = useState<PlateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleAuthError = handleAuthErrorShared;

  // Use provided lang or fallback to i18n.language or navigator.language
  const browserLang = typeof navigator !== 'undefined' ? navigator.language : undefined;
  const currentLang = resolveSetupLang(lang, i18n.language, browserLang);

  const enabled = !!values;

  useEffect(() => {
    if (!enabled) {
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
            lang: currentLang,
          },
          {
            signal: abortController.signal,
            onAuthError: handleAuthError,
          },
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
          {
            signal: abortController.signal,
            onAuthError: handleAuthError,
          },
        );

        const [bmrResult, plateResult] = await Promise.all([bmrPromise, platePromise]);

        if (!bmrResult) {
          throw new Error('BMR API returned empty response');
        }

        if (!plateResult) {
          throw new Error('Plate API returned empty response');
        }

        setBmrData(normalizeBmrResponse(bmrResult, values.activity));
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
  }, [enabled, values, currentLang, retryKey]);

  return {
    bmrData,
    plateData,
    loading,
    error,
    enabled,
  };
}

export function useTargets(values: SetupFormValues | null, lang?: SetupSupportedLang, retryKey?: number) {
  const { i18n } = useTranslation();
  const [data, setData] = useState<TargetsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const latestRequestIdRef = useRef(0);
  const browserLang = typeof navigator !== 'undefined' ? navigator.language : undefined;
  const effectiveLang = resolveSetupLang(lang, i18n.language, browserLang);

  const handleAuthError = (code: 401 | 403, _helpers: { clearApiKey: () => void }) => {
    console.warn(`[auth] Targets API error: ${code}`);
  };

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

    // Increment request ID to track this specific request
    latestRequestIdRef.current += 1;
    const requestId = latestRequestIdRef.current;

    const fetchTargets = async () => {
      // Only update state if this is still the latest request
      if (requestId !== latestRequestIdRef.current) return;

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
            lang: effectiveLang,
          },
          {
            signal: abortController.signal,
            onAuthError: handleAuthError,
          },
        );

        // Only update state if this is still the latest request
        if (requestId === latestRequestIdRef.current) {
          setData(normalizeTargetsResponse(response, effectiveLang));
        }
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          return;
        }
        // Only update state if this is still the latest request
        if (requestId === latestRequestIdRef.current) {
          console.error('Targets fetch error:', err);
          setError(err instanceof Error ? err.message : 'Unknown error');
        }
      } finally {
        // Only update state if this is still the latest request
        if (requestId === latestRequestIdRef.current) {
          setLoading(false);
        }
      }
    };

    fetchTargets();

    return () => {
      abortController.abort();
    };
  }, [values, effectiveLang, retryKey]);

  return {
    data,
    loading,
    error,
  };
}

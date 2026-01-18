// RU: Страница расчета BMI - форма ввода параметров и отображение результата
// EN: BMI calculation page - input form and result display

import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { calculateBMI } from '../../api/bmi';
import SoftPaywallHook from '../../components/SoftPaywallHook';
import type { components } from '../../api/schema';

type BMICalculateRequest = components['schemas']['BMICalculateRequest'];
type BMICalculateResponse = components['schemas']['BMICalculateResponse'];

/**
 * Normalize numeric input: replace comma with dot, trim whitespace.
 * Used for locale-aware parsing (RU uses comma as decimal separator).
 */
const normalizeNumber = (value: string): string => {
  return value.replace(/,/g, '.').trim();
};

export default function BMICalculatePage(): JSX.Element {
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<BMICalculateResponse | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Form state
  const [weightKg, setWeightKg] = useState<string>('');
  const [heightCm, setHeightCm] = useState<string>('');
  const [sex, setSex] = useState<'male' | 'female'>('female');
  const [age, setAge] = useState<string>('');
  const [waistCm, setWaistCm] = useState<string>('');
  const [athlete, setAthlete] = useState<boolean>(false);
  const [pregnant, setPregnant] = useState<boolean>(false);
  // Note: hip_cm intentionally omitted on FREE tier UI (schema supports PRO/WHR flows)

  // Determine language from i18n (fallback to 'en')
  const getLang = (): 'ru' | 'en' | 'es' => {
    const lang = i18n.language.toLowerCase();
    if (lang.startsWith('ru')) return 'ru';
    if (lang.startsWith('es')) return 'es';
    return 'en';
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError(null);
    setResponse(null);

    // Abort previous request if any
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // Normalize and parse numeric inputs (support comma decimals for RU locale)
    const normalizedWeight = normalizeNumber(weightKg);
    const normalizedHeight = normalizeNumber(heightCm);
    const normalizedWaist = normalizeNumber(waistCm);

    const parsedWeightKg = parseFloat(normalizedWeight);
    const parsedHeightCm = parseFloat(normalizedHeight);
    const parsedWaistCm = parseFloat(normalizedWaist);

    // Validate weight (required, must be positive)
    if (!Number.isFinite(parsedWeightKg) || parsedWeightKg <= 0) {
      setError(t('bmiCalculate.error.invalidWeight'));
      return;
    }

    // Validate height (required, must be positive)
    if (!Number.isFinite(parsedHeightCm) || parsedHeightCm <= 0) {
      setError(t('bmiCalculate.error.invalidHeight'));
      return;
    }

    // Validate age (required by schema, must be positive and reasonable)
    const parsedAge = parseInt(age.trim(), 10);
    if (!Number.isFinite(parsedAge) || parsedAge <= 0 || parsedAge > 120) {
      setError(t('bmiCalculate.error.invalidAge'));
      return;
    }

    // Create new AbortController for this request
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setLoading(true);
    try {
      const request: BMICalculateRequest = {
        weight_kg: parsedWeightKg,
        height_cm: parsedHeightCm,
        gender: sex, // Schema uses 'gender', not 'sex'
        age: parsedAge,
        waist_cm: Number.isFinite(parsedWaistCm) && parsedWaistCm > 0 ? parsedWaistCm : undefined,
        athlete,
        pregnant,
        lang: getLang(),
      };

      const result = await calculateBMI(request, { signal: abortController.signal });

      // Update only if this controller is still the latest one
      if (abortControllerRef.current === abortController && !abortController.signal.aborted) {
        setResponse(result);
      }
    } catch (err) {
      // Ignore AbortError (request was cancelled)
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      // Only set error if this controller is still current
      if (abortControllerRef.current === abortController) {
        setError(err instanceof Error ? err.message : t('bmiCalculate.error.generic'));
        setResponse(null);
      }
    } finally {
      // Clear loading only if this request is still current
      if (abortControllerRef.current === abortController) {
        abortControllerRef.current = null;
        setLoading(false);
      }
    }
  };

  const handleReset = (): void => {
    setResponse(null);
    setError(null);
    setWeightKg('');
    setHeightCm('');
    setAge('');
    setWaistCm('');
    setAthlete(false);
    setPregnant(false);
    // Abort any pending request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-4 pb-20">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text mb-2">{t('bmiCalculate.title')}</h1>
        <p className="text-muted">{t('bmiCalculate.description')}</p>
      </div>

      {!response ? (
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl p-6 shadow-sm space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label htmlFor="weight-input" className="block text-sm font-medium text-text">{t('bmiCalculate.form.weightLabel')}</label>
              <input
                id="weight-input"
                type="number"
                step="0.1"
                value={weightKg}
                onChange={(e) => setWeightKg(e.target.value)}
                required
                className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                placeholder="70.0"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="height-input" className="block text-sm font-medium text-text">{t('bmiCalculate.form.heightLabel')}</label>
              <input
                id="height-input"
                type="number"
                step="0.1"
                value={heightCm}
                onChange={(e) => setHeightCm(e.target.value)}
                required
                className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                placeholder="170.0"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="sex-input" className="block text-sm font-medium text-text">{t('bmiCalculate.form.sexLabel')}</label>
              <select
                id="sex-input"
                value={sex}
                onChange={(e) => setSex(e.target.value as 'male' | 'female')}
                className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
              >
                <option value="female">{t('bmiCalculate.form.sex.female')}</option>
                <option value="male">{t('bmiCalculate.form.sex.male')}</option>
              </select>
            </div>

            <div className="space-y-2">
              <label htmlFor="age-input" className="block text-sm font-medium text-text">{t('bmiCalculate.form.ageLabel')}</label>
              <input
                id="age-input"
                type="number"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                required
                min="1"
                max="120"
                className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                placeholder="30"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="waist-input" className="block text-sm font-medium text-text">{t('bmiCalculate.form.waistLabel')}</label>
              <input
                id="waist-input"
                type="number"
                step="0.1"
                value={waistCm}
                onChange={(e) => setWaistCm(e.target.value)}
                className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                placeholder="80.0"
              />
            </div>

            <label
              htmlFor="athlete-input"
              className="flex items-center gap-3 px-4 py-3 border border-muted rounded-xl bg-white text-text"
            >
              <input
                id="athlete-input"
                type="checkbox"
                checked={athlete}
                onChange={(e) => setAthlete(e.target.checked)}
                className="h-4 w-4 accent-primary"
              />
              <span className="text-sm font-medium">{t('bmiCalculate.form.athleteLabel')}</span>
            </label>

            <label
              htmlFor="pregnant-input"
              className="flex items-center gap-3 px-4 py-3 border border-muted rounded-xl bg-white text-text"
            >
              <input
                id="pregnant-input"
                type="checkbox"
                checked={pregnant}
                onChange={(e) => setPregnant(e.target.checked)}
                className="h-4 w-4 accent-primary"
              />
              <span className="text-sm font-medium">{t('bmiCalculate.form.pregnantLabel')}</span>
            </label>
          </div>

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-800">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !weightKg || !heightCm || !age}
            className="w-full py-3 bg-primary text-navy rounded-xl hover:bg-primary/90 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? t('bmiCalculate.form.submitting') : t('bmiCalculate.form.submit')}
          </button>
        </form>
      ) : (
        <div className="space-y-4">
          {/* BMI Result Card */}
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <h2 className="text-xl font-bold text-text mb-4">{t('bmiCalculate.result.title')}</h2>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-muted">{t('bmiCalculate.result.bmi')}</span>
                <span className="font-semibold text-text">{response.bmi.toFixed(1)}</span>
              </div>
              {response.category && (
                <div className="flex justify-between">
                  <span className="text-muted">{t('bmiCalculate.result.category')}</span>
                  <span className="font-semibold text-text">{response.category}</span>
                </div>
              )}
              {response.interpretation && (
                <div className="mt-4 p-3 bg-navy/5 rounded-lg">
                  <p className="text-sm text-muted">{response.interpretation}</p>
                </div>
              )}
            </div>
          </div>

          {/* Soft Paywall Hook (post-result position) */}
          {response.soft_paywall && (
            <SoftPaywallHook hook={response.soft_paywall} />
          )}

          {/* Reset Button */}
          <button
            onClick={handleReset}
            disabled={loading}
            className="w-full py-3 bg-muted/20 text-text rounded-xl hover:bg-muted/30 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {t('bmiCalculate.form.reset')}
          </button>
        </div>
      )}
    </div>
  );
}

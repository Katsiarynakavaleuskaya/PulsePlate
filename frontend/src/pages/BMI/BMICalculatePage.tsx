// RU: Страница расчета BMI - форма ввода параметров и отображение результата
// EN: BMI calculation page - input form and result display

import { useEffect, useMemo, useRef, useState } from 'react';
import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';
import { calculateBMI } from '../../api/bmi';
import type { components } from '../../api/schema';
import SoftPaywallHook from '../../components/SoftPaywallHook';
import { NumberInput, buttonClasses } from '../../components/ui';

type BMICalculateRequest = components['schemas']['BMICalculateRequest'];
type BMICalculateResponse = components['schemas']['BMICalculateResponse'];

/**
 * Normalize numeric input: replace comma with dot, trim whitespace.
 * Used for locale-aware parsing (RU uses comma as decimal separator).
 */
const normalizeNumber = (value: string): string => {
  return value.replace(/,/g, '.').trim();
};

// RU: Возраст принимаем только как целое число без неявного округления.
// EN: Accept age only as an integer and reject silent truncation.
const parseIntegerInput = (value: string): number => {
  const normalizedValue = normalizeNumber(value);
  if (normalizedValue === '') {
    return Number.NaN;
  }

  const parsedValue = Number(normalizedValue);
  return Number.isInteger(parsedValue) ? parsedValue : Number.NaN;
};

function MetricChip({ label }: { label: string }): JSX.Element {
  return (
    <span className="rounded-full bg-white/[0.08] px-4 py-1.5 text-xs font-medium text-white/88">
      {label}
    </span>
  );
}

function SurfaceField({
  label,
  children,
}: {
  label: string;
  children: JSX.Element;
}): JSX.Element {
  return (
    <label className="block rounded-2xl border border-white/12 bg-white/[0.08] p-4">
      <span className="mb-2 block text-sm font-medium text-white/72">{label}</span>
      {children}
    </label>
  );
}

function SegmentedChoice<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: readonly { label: string; value: T }[];
  value: T;
  onChange: (value: T) => void;
}): JSX.Element {
  return (
    <div className="rounded-2xl border border-white/12 bg-white/[0.08] p-4">
      <p className="mb-3 text-sm font-medium text-white/72">{label}</p>
      <div className="grid grid-cols-2 gap-3">
        {options.map((option) => {
          const isActive = option.value === value;
          return (
            <button
              key={option.value}
              type="button"
              className={[
                'rounded-full px-4 py-2 text-sm font-semibold transition',
                isActive
                  ? 'bg-white/[0.18] text-white'
                  : 'bg-white/[0.06] text-white/62 hover:bg-white/[0.1]',
              ].join(' ')}
              onClick={() => onChange(option.value)}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function BMICalculatePage(): JSX.Element {
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<BMICalculateResponse | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const [weightKg, setWeightKg] = useState<string>('');
  const [heightCm, setHeightCm] = useState<string>('');
  const [sex, setSex] = useState<'male' | 'female'>('female');
  const [age, setAge] = useState<string>('');
  const [waistCm, setWaistCm] = useState<string>('');
  const [athlete, setAthlete] = useState<boolean>(false);
  const [pregnant, setPregnant] = useState<boolean>(false);

  const numberLocale = i18n.language.toLowerCase().startsWith('ru') ? 'ru' : 'en';
  const hasResult = !loading && response !== null;

  const resultSummary = useMemo(() => {
    if (!response) {
      return {
        value: '--',
        detail: t('bmiCalculate.summary.emptyDetail'),
      };
    }

    return {
      value: response.bmi.toFixed(1),
      detail: response.interpretation ?? response.category ?? t('bmiCalculate.summary.fallbackDetail'),
    };
  }, [response, t]);

  const getLang = (): 'ru' | 'en' | 'es' => {
    const lang = i18n.language.toLowerCase();
    if (lang.startsWith('ru')) return 'ru';
    if (lang.startsWith('es')) return 'es';
    return 'en';
  };

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setError(null);
    setResponse(null);

    abortControllerRef.current?.abort();
    abortControllerRef.current = null;

    const parsedWeightKg = parseFloat(normalizeNumber(weightKg));
    const parsedHeightCm = parseFloat(normalizeNumber(heightCm));
    const parsedWaistCm = parseFloat(normalizeNumber(waistCm));
    const parsedAge = parseIntegerInput(age);

    if (!Number.isFinite(parsedWeightKg) || parsedWeightKg <= 0) {
      setError(t('bmiCalculate.error.invalidWeight'));
      return;
    }

    if (!Number.isFinite(parsedHeightCm) || parsedHeightCm <= 0) {
      setError(t('bmiCalculate.error.invalidHeight'));
      return;
    }

    if (!Number.isFinite(parsedAge) || parsedAge <= 0 || parsedAge > 120) {
      setError(t('bmiCalculate.error.invalidAge'));
      return;
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    setLoading(true);

    try {
      const request: BMICalculateRequest = {
        weight_kg: parsedWeightKg,
        height_cm: parsedHeightCm,
        gender: sex,
        age: parsedAge,
        waist_cm: Number.isFinite(parsedWaistCm) && parsedWaistCm > 0 ? parsedWaistCm : undefined,
        athlete,
        pregnant,
        lang: getLang(),
      };

      const result = await calculateBMI(request, { signal: abortController.signal });

      if (abortControllerRef.current === abortController && !abortController.signal.aborted) {
        setResponse(result);
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      if (abortControllerRef.current === abortController) {
        setError(err instanceof Error ? err.message : t('bmiCalculate.error.generic'));
        setResponse(null);
      }
    } finally {
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
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
  };

  return (
    <main className="min-h-screen bg-[var(--pp-navy)] px-4 py-6 text-white sm:px-6">
      <div className="mx-auto max-w-[24rem] space-y-6">
        <section className="rounded-[1.5rem] border border-white/12 bg-white/[0.08] p-5 shadow-[0_28px_56px_rgba(0,0,0,0.3)]">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-white/52">
            {t('bmiCalculate.hero.eyebrow')}
          </p>
          <h1 className="mt-2 text-[2.1rem] font-bold leading-none text-white">{t('bmiCalculate.title')}</h1>
          <p className="mt-3 text-sm leading-6 text-white/62">{t('bmiCalculate.description')}</p>
          <div className="mt-5 flex flex-wrap gap-2">
            <MetricChip label={t('bmiCalculate.hero.metrics.weight')} />
            <MetricChip label={t('bmiCalculate.hero.metrics.height')} />
            <MetricChip label={t('bmiCalculate.hero.metrics.context')} />
          </div>
        </section>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <h2 className="text-xl font-semibold text-white">{t('bmiCalculate.form.sectionTitle')}</h2>

          <SurfaceField label={t('bmiCalculate.form.weightLabel')}>
            <NumberInput
              locale={numberLocale}
              placeholder="70.0"
              value={weightKg === '' ? '' : Number(weightKg)}
              onValueChange={(value) => setWeightKg(value === '' ? '' : String(value))}
            />
          </SurfaceField>

          <SurfaceField label={t('bmiCalculate.form.heightLabel')}>
            <NumberInput
              locale={numberLocale}
              placeholder="170.0"
              value={heightCm === '' ? '' : Number(heightCm)}
              onValueChange={(value) => setHeightCm(value === '' ? '' : String(value))}
            />
          </SurfaceField>

          <SurfaceField label={t('bmiCalculate.form.ageLabel')}>
            <NumberInput
              inputMode="numeric"
              locale={numberLocale}
              placeholder="30"
              value={age === '' ? '' : Number(age)}
              onValueChange={(value) => setAge(value === '' ? '' : String(value))}
            />
          </SurfaceField>

          <SurfaceField label={t('bmiCalculate.form.waistLabel')}>
            <NumberInput
              locale={numberLocale}
              placeholder="80.0"
              value={waistCm === '' ? '' : Number(waistCm)}
              onValueChange={(value) => setWaistCm(value === '' ? '' : String(value))}
            />
          </SurfaceField>

          <SegmentedChoice<'male' | 'female'>
            label={t('bmiCalculate.form.sexLabel')}
            options={[
              { label: t('bmiCalculate.form.sex.male'), value: 'male' },
              { label: t('bmiCalculate.form.sex.female'), value: 'female' },
            ]}
            value={sex}
            onChange={setSex}
          />

          <div className="rounded-2xl border border-white/12 bg-white/[0.08] p-4">
            <p className="mb-3 text-sm font-medium text-white/72">{t('bmiCalculate.form.contextTitle')}</p>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                className={[
                  'rounded-full px-4 py-2 text-sm font-semibold transition',
                  athlete ? 'bg-white/[0.18] text-white' : 'bg-white/[0.06] text-white/62 hover:bg-white/[0.1]',
                ].join(' ')}
                onClick={() => setAthlete((prev) => !prev)}
              >
                {t('bmiCalculate.form.athleteLabel')}
              </button>
              <button
                type="button"
                className={[
                  'rounded-full px-4 py-2 text-sm font-semibold transition',
                  pregnant
                    ? 'bg-white/[0.18] text-white'
                    : 'bg-white/[0.06] text-white/62 hover:bg-white/[0.1]',
                ].join(' ')}
                onClick={() => setPregnant((prev) => !prev)}
              >
                {t('bmiCalculate.form.pregnantLabel')}
              </button>
            </div>
          </div>

          {error ? (
            <div className="rounded-2xl border border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">
              {error}
            </div>
          ) : null}

          <button
            className={buttonClasses({
              fullWidth: true,
              className: 'rounded-2xl text-white shadow-none',
            })}
            disabled={loading || !weightKg || !heightCm || !age}
            type="submit"
          >
            {loading ? t('bmiCalculate.form.submitting') : t('bmiCalculate.form.submit')}
          </button>
        </form>

        <section className="rounded-[1.5rem] border border-white/12 bg-white/[0.08] p-5">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-white/72">{t('bmiCalculate.result.title')}</p>
            <p className="text-3xl font-semibold text-white">{resultSummary.value}</p>
          </div>
          <div className="mt-6 grid grid-cols-4 gap-3">
            {[1, 2, 3, 4].map((index) => (
              <div
                key={index}
                className={[
                  'h-2 rounded-full transition',
                  hasResult ? 'bg-[var(--color-primary)]/55' : 'bg-white/22',
                ].join(' ')}
              />
            ))}
          </div>
          <div className="mt-6 rounded-[1.25rem] border border-white/10 bg-white/[0.04] p-4">
            <p className="text-sm leading-6 text-white/72">{resultSummary.detail}</p>
          </div>
        </section>

        {response?.soft_paywall ? <SoftPaywallHook hook={response.soft_paywall} /> : null}

        {response ? (
          <button
            className={buttonClasses({
              variant: 'secondary',
              fullWidth: true,
              className: 'rounded-2xl border-white/12 bg-white/[0.06] text-white hover:bg-white/[0.1]',
            })}
            disabled={loading}
            onClick={handleReset}
            type="button"
          >
            {t('bmiCalculate.form.reset')}
          </button>
        ) : null}
      </div>
    </main>
  );
}

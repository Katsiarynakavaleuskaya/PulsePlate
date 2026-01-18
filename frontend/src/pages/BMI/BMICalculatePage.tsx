// RU: Страница расчета BMI - форма ввода параметров и отображение результата
// EN: BMI calculation page - input form and result display

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { calculateBMI } from '../../api/bmi';
import SoftPaywallHook from '../../components/SoftPaywallHook';
import type { components } from '../../api/schema';

type BMICalculateRequest = components['schemas']['BMICalculateRequest'];
type BMICalculateResponse = components['schemas']['BMICalculateResponse'];

export default function BMICalculatePage() {
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<BMICalculateResponse | null>(null);

  // Form state
  const [weightKg, setWeightKg] = useState<string>('');
  const [heightCm, setHeightCm] = useState<string>('');
  const [sex, setSex] = useState<'male' | 'female'>('female');
  const [age, setAge] = useState<string>('');
  const [waistCm, setWaistCm] = useState<string>('');
  const [hipCm, setHipCm] = useState<string>('');

  // Determine language from i18n (fallback to 'en')
  const getLang = (): 'ru' | 'en' | 'es' => {
    const lang = i18n.language.toLowerCase();
    if (lang.startsWith('ru')) return 'ru';
    if (lang.startsWith('es')) return 'es';
    return 'en';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const request: BMICalculateRequest = {
        weight_kg: parseFloat(weightKg),
        height_cm: parseFloat(heightCm),
        sex,
        age: age ? parseInt(age, 10) : undefined,
        waist_cm: waistCm ? parseFloat(waistCm) : undefined,
        hip_cm: hipCm ? parseFloat(hipCm) : undefined,
        lang: getLang(),
      };

      const result = await calculateBMI(request);
      setResponse(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setResponse(null);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setResponse(null);
    setError(null);
    setWeightKg('');
    setHeightCm('');
    setAge('');
    setWaistCm('');
    setHipCm('');
  };

  return (
    <div className="max-w-2xl mx-auto p-4 pb-20">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text mb-2">BMI Calculator</h1>
        <p className="text-muted">Calculate your Body Mass Index</p>
      </div>

      {!response ? (
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl p-6 shadow-sm space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-text">Weight (kg)</label>
              <input
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
              <label className="block text-sm font-medium text-text">Height (cm)</label>
              <input
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
              <label className="block text-sm font-medium text-text">Sex</label>
              <select
                value={sex}
                onChange={(e) => setSex(e.target.value as 'male' | 'female')}
                className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
              >
                <option value="female">Female</option>
                <option value="male">Male</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-text">Age (optional)</label>
              <input
                type="number"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                placeholder="30"
              />
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-text">Waist (cm, optional)</label>
              <input
                type="number"
                step="0.1"
                value={waistCm}
                onChange={(e) => setWaistCm(e.target.value)}
                className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                placeholder="80.0"
              />
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-text">Hip (cm, optional)</label>
              <input
                type="number"
                step="0.1"
                value={hipCm}
                onChange={(e) => setHipCm(e.target.value)}
                className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                placeholder="95.0"
              />
            </div>
          </div>

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-800">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !weightKg || !heightCm}
            className="w-full py-3 bg-primary text-navy rounded-xl hover:bg-primary/90 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Calculating...' : 'Calculate BMI'}
          </button>
        </form>
      ) : (
        <div className="space-y-4">
          {/* BMI Result Card */}
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <h2 className="text-xl font-bold text-text mb-4">BMI Result</h2>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-muted">BMI:</span>
                <span className="font-semibold text-text">{response.bmi.toFixed(1)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Category:</span>
                <span className="font-semibold text-text">{response.category}</span>
              </div>
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
            className="w-full py-3 bg-muted/20 text-text rounded-xl hover:bg-muted/30 transition-colors font-medium"
          >
            Calculate Again
          </button>
        </div>
      )}
    </div>
  );
}

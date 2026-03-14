// RU: Форма ввода параметров пользователя для расчета питания
// EN: User parameters input form for nutrition calculation

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { setupSchema, type SetupFormValues, validDietFlags, type DietFlag } from './schema';
import { useSettings } from '../../lib/settings';
import { useTranslation } from 'react-i18next';

interface SetupFormProps {
  onSubmit: (values: SetupFormValues) => void;
}

function normalizeNumericInput(value: unknown, { integer = false }: { integer?: boolean } = {}): number | undefined {
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      return undefined;
    }
    return integer ? Math.trunc(value) : value;
  }

  const normalized = String(value ?? '').trim().replace(',', '.');
  if (!normalized) {
    return undefined;
  }

  const parsed = Number(normalized);
  if (!Number.isFinite(parsed)) {
    return undefined;
  }

  return integer ? Math.trunc(parsed) : parsed;
}

export default function SetupForm({ onSubmit }: SetupFormProps) {
  const { settings, updateSetting } = useSettings();
  const { t } = useTranslation();

  // Get saved values or defaults with validation
  const saved: SetupFormValues | undefined = (() => {
    const result = setupSchema.safeParse(settings.setup);
    return result.success ? result.data : undefined;
  })();

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<SetupFormValues>({
    resolver: zodResolver(setupSchema),
    defaultValues: saved ?? {
      sex: 'female',
      age: 30,
      height_cm: 170,
      weight_kg: 65,
      activity: 'moderate',
      goal: 'maintain',
      diet_flags: [],
    },
  });

  // Watch diet_flags to manage checkbox states
  const watchedDietFlags = watch('diet_flags') || [];

  // Handle checkbox changes for diet flags
  const handleDietFlagChange = (flag: DietFlag, checked: boolean) => {
    const currentFlags = watchedDietFlags || [];
    const newFlags = checked
      ? currentFlags.includes(flag) ? currentFlags : [...currentFlags, flag]
      : currentFlags.filter(f => f !== flag);
    setValue('diet_flags', newFlags as DietFlag[]);
  };

  const submit = (values: SetupFormValues) => {
    // Save to settings
    updateSetting('setup', values);
    onSubmit(values);
  };

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text mb-2">{t('nutritionSetup.title')}</h1>
        <p className="text-muted">{t('nutritionSetup.description')}</p>
      </div>

      <form onSubmit={handleSubmit(submit)} className="space-y-6">
        {/* Basic Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-text">{t('nutrition.sex.label')}</label>
            <select
              {...register('sex')}
              className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
            >
              <option value="female">{t('nutrition.sex.female')}</option>
              <option value="male">{t('nutrition.sex.male')}</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-text">{t('nutrition.age')}</label>
            <input
              type="text"
              inputMode="numeric"
              {...register('age', { setValueAs: (value) => normalizeNumericInput(value, { integer: true }) })}
              placeholder="30"
              className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
            />
            {errors.age && <p className="text-sm text-red-600">{errors.age.message}</p>}
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-text">{t('nutrition.height_cm')}</label>
            <input
              type="text"
              inputMode="decimal"
              {...register('height_cm', { setValueAs: (value) => normalizeNumericInput(value) })}
              placeholder="170"
              className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
            />
            {errors.height_cm && <p className="text-sm text-red-600">{errors.height_cm.message}</p>}
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-text">{t('nutrition.weight_kg')}</label>
            <input
              type="text"
              inputMode="decimal"
              {...register('weight_kg', { setValueAs: (value) => normalizeNumericInput(value) })}
              placeholder="65"
              className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
            />
            {errors.weight_kg && <p className="text-sm text-red-600">{errors.weight_kg.message}</p>}
          </div>
        </div>

        {/* Activity Level */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-text">{t('nutrition.activity.label')}</label>
          <select
            {...register('activity')}
            className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
          >
            <option value="sedentary">{t('nutrition.activity.options.sedentary')}</option>
            <option value="light">{t('nutrition.activity.options.light')}</option>
            <option value="moderate">{t('nutrition.activity.options.moderate')}</option>
            <option value="active">{t('nutrition.activity.options.active')}</option>
            <option value="athlete">{t('nutrition.activity.options.athlete')}</option>
          </select>
        </div>

        {/* Goal */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-text">{t('nutrition.goal.label')}</label>
          <select
            {...register('goal')}
            className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
          >
            <option value="lose">{t('nutrition.goal.options.lose')}</option>
            <option value="maintain">{t('nutrition.goal.options.maintain')}</option>
            <option value="gain">{t('nutrition.goal.options.gain')}</option>
          </select>
        </div>

        {/* Diet Flags */}
        <div className="space-y-3">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-text">
              {t('nutrition.dietFlags.label')}
              <span className="text-xs text-muted"> ({t('nutrition.dietFlags.optional')})</span>
            </label>
            <p className="text-xs text-muted">{t('nutrition.dietFlags.description')}</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {validDietFlags.map((flag) => (
              <label key={flag} className="flex items-center space-x-3 p-3 border border-muted rounded-xl hover:bg-gray-50 transition-colors cursor-pointer">
                <input
                  type="checkbox"
                  checked={watchedDietFlags.includes(flag)}
                  onChange={(e) => handleDietFlagChange(flag, e.target.checked)}
                  className="w-4 h-4 text-primary border-gray-300 rounded focus:ring-primary focus:ring-2"
                />
                <span className="text-sm text-text">{t(`nutrition.dietFlags.${flag}`)}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          className="w-full py-4 px-6 bg-primary text-navy rounded-xl font-semibold text-base hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary/20 transition-colors min-h-[44px]"
        >
          {t('nutritionSetup.calculateButton')}
        </button>

        <p className="text-xs text-muted text-center">
          {t('nutritionSetup.saveNote')}
        </p>
      </form>
    </div>
  );
}

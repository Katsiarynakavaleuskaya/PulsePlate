// RU: Форма ввода параметров пользователя для расчета питания
// EN: User parameters input form for nutrition calculation

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { setupSchema, type SetupFormValues } from './schema';
import { useSettings } from '../../lib/settings';

interface SetupFormProps {
  onSubmit: (values: SetupFormValues) => void;
}

export default function SetupForm({ onSubmit }: SetupFormProps) {
  const { settings, updateSetting } = useSettings();

  // Get saved values or defaults with validation
  const saved: SetupFormValues | undefined = (() => {
    const result = setupSchema.safeParse(settings.setup);
    return result.success ? result.data : undefined;
  })();

  const { register, handleSubmit, formState: { errors } } = useForm<SetupFormValues>({
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

  const submit = (values: SetupFormValues) => {
    // Save to settings
    updateSetting('setup', values);
    onSubmit(values);
  };

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text mb-2">Настройка питания</h1>
        <p className="text-muted">Заполните информацию для персонального расчета калорий и макронутриентов</p>
      </div>

      <form onSubmit={handleSubmit(submit)} className="space-y-6">
        {/* Basic Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-text">Пол</label>
            <select
              {...register('sex')}
              className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
            >
              <option value="female">Женский</option>
              <option value="male">Мужской</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-text">Возраст</label>
            <input
              type="number"
              {...register('age', { valueAsNumber: true })}
              placeholder="30"
              className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
            />
            {errors.age && <p className="text-sm text-red-600">{errors.age.message}</p>}
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-text">Рост (см)</label>
            <input
              type="number"
              {...register('height_cm', { valueAsNumber: true })}
              placeholder="170"
              className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
            />
            {errors.height_cm && <p className="text-sm text-red-600">{errors.height_cm.message}</p>}
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-text">Вес (кг)</label>
            <input
              type="number"
              {...register('weight_kg', { valueAsNumber: true })}
              placeholder="65"
              className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
            />
            {errors.weight_kg && <p className="text-sm text-red-600">{errors.weight_kg.message}</p>}
          </div>
        </div>

        {/* Activity Level */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-text">Уровень активности</label>
          <select
            {...register('activity')}
            className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
          >
            <option value="sedentary">Сидячий образ жизни</option>
            <option value="light">Легкая активность (1-3 раза в неделю)</option>
            <option value="moderate">Умеренная активность (3-5 раз в неделю)</option>
            <option value="active">Высокая активность (6-7 раз в неделю)</option>
            <option value="athlete">Профессиональный спортсмен</option>
          </select>
        </div>

        {/* Goal */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-text">Цель</label>
          <select
            {...register('goal')}
            className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
          >
            <option value="lose">Похудение</option>
            <option value="maintain">Поддержание веса</option>
            <option value="gain">Набор веса</option>
          </select>
        </div>

        {/* Diet Flags */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-text">Особенности питания (необязательно)</label>
        <input
          placeholder="VEG, GF, DAIRY_FREE, LOW_COST (через запятую)"
          {...register('diet_flags', {
            setValueAs: (value: string | undefined) =>
              value && value.trim() ? value.split(',').map(s => s.trim()) : []
          })}
          className="w-full px-4 py-3 border border-muted rounded-xl bg-white text-text focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
        />
          <p className="text-xs text-muted">Укажите предпочтения или ограничения в питании</p>
        </div>

        {/* Submit */}
        <button
          type="submit"
          className="w-full py-4 px-6 bg-primary text-navy rounded-xl font-semibold text-base hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary/20 transition-colors min-h-[44px]"
        >
          Рассчитать персональную тарелку
        </button>

        <p className="text-xs text-muted text-center">
          Данные сохраняются локально и используются для расчета вашего рациона
        </p>
      </form>
    </div>
  );
}

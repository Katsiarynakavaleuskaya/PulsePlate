# Подготовка визуального QA FitChef RU

Классификация: `INTERNAL_REVIEW_ONLY`.

Этот файл ускоряет ручную проверку отрендеренных кадров RU App Store pack.
Он не меняет метаданные, сценарии, копирайт, Fastlane или App Store Connect.
Экспорт изображений, экспорт preview-видео и отправка материалов остаются вне области этого prep-артефакта.

## Источники

- EN manifest: `appstore/fitchef/en-US/iphone-6.9/screenshots/shot_manifest.json`
- RU manifest: `appstore/fitchef/ru-RU/iphone-6.9/screenshots/shot_manifest.json`
- EN storyboard: `appstore/fitchef/en-US/iphone-6.9/preview/storyboard.json`
- RU storyboard: `appstore/fitchef/ru-RU/iphone-6.9/preview/storyboard.json`
- Safe area: `top=260px`, `bottom=260px`, `left_right=120px`

## Ручная проверка

| Shot | Файл | Scene | Time | Product surface | Mascot | RU max line | Источники | Что проверить в рендере |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| `shot-01` | `01_core-value.png` | `scene-01` | `0-3s` | dashboard / daily overview | FitChefOnboardingWelcome | 15 | `ios/PulsePlate/Views/HomeView.swift`; `frontend/src/pages/Home.tsx` | Проверить перенос строки с `AI`, читаемость логотипа и отсутствие перекрытия FitChef. |
| `shot-02` | `02_nutrition-analysis.png` | `scene-02` | `3-6s` | nutrition analysis / result view | FitChefThinking | 14 | `frontend/src/pages/NutritionSetup/ResultView.tsx`; `frontend/src/pages/NutritionSetup/MacroCards.tsx`; `frontend/src/pages/NutritionSetup/MicrosGrid.tsx` | Проверить плотность слова `Микронутриенты` и видимость карточек анализа. |
| `shot-03` | `03_meal-planner.png` | `scene-03` | `6-9s` | weekly planner | FitChefThinking | 15 | `ios/PulsePlate/Views/WeeklyPlan/WeeklyPlanReaderView.swift`; `ios/PulsePlate/ViewModels/WeeklyPlanReaderViewModel.swift`; `frontend/src/features/weekly-plan/hooks/useWeeklyPlan.ts` | Проверить перенос `AI-план питания` и нейтральную формулировку целей без обещаний результата. |
| `shot-04` | `04_grocery-list.png` | `scene-04` | `9-12s` | shopping list | FitChef | 16 | `frontend/src/features/shoplist/ShoplistPreview.tsx`; `ios/PulsePlate/ViewModels/ShoppingListReaderViewModel.swift`; `ios/PulsePlate/Views/HomeView.swift` | Проверить строку `в удобный список`, safe area и FitChef рядом со списком покупок. |
| `shot-05` | `05_health-progress.png` | `scene-05` | `12-15s` | progress and weekly analytics | FitChefWink | 19 | `ios/PulsePlate/Views/ProgressView.swift`; `ios/PulsePlate/Views/WeeklyProgressView.swift`; `frontend/src/pages/Progress.tsx` | Проверить самую длинную RU-строку `Еженедельные выводы`, переносы и сохранение прогресса как наблюдений. |
| `shot-06` | `06_personalization.png` | `scene-06` | `15-18s` | profile and setup | FitChefThinking | 13 | `ios/PulsePlate/Views/ProfileView.swift`; `frontend/src/pages/Profile.tsx`; `frontend/src/pages/NutritionSetup/SetupForm.tsx` | Проверить компактность блока целей, предпочтений и типов рационов без перегруза кадра. |
| `shot-07` | `07_ai-assistant.png` | `scene-07` | `18-22s` | bounded assistant / insight view | FitChef | 12 | `ios/PulsePlate/Views/AIInsightView.swift`; `frontend/src/pages/Home.tsx`; `app/routers/fitchef_insight.py` | Проверить `AI-гид` как навигационный текст приложения и отсутствие обещаний результата. |

## Чеклист рендера

- Все семь кадров идут в порядке `shot_manifest.json`.
- Каждая сцена сохраняет timing из `storyboard.json`.
- Заголовок остается максимум в две видимые строки.
- Поддерживающий текст не перекрывает ключевой UI или FitChef.
- Реальный UI остается главным визуальным объектом кадра.
- Текст не добавляет ценовые обещания, обещания результата или новые функции.
- Итог проверки фиксируется как ручной review note, а не как доказательство
  отправки материалов.

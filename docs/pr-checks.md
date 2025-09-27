# PR Common Checks

## Accessibility (a11y)
- Контраст текста и ключевых элементов ≥4.5:1.
- Навигация клавиатурой и фокус виден.
- VoiceOver / aria-label / Dynamic Type, touch targets ≥44×44pt.

## Security & Privacy
- Нет секретов и токенов в репозитории (используем .env.example).
- Личные данные не логируем, ошибки обрабатываем аккуратно.
- HealthKit / StoreKit — понятные разрешения и копирайт в UI.

## Performance
- Оцените влияние на bundle size, рендеры, FPS или память.
- Веб: используйте tree-shaking, кэширование, избегайте лишних deps.
- iOS: проверяйте размер билда и производительность в Simulator/Device.

## Marketing & GTM
- Локализации EN/RU/ES актуальны.
- События аналитики (paywall_*, purchase_*, restore_*) добавлены при необходимости.

## Documentation
- README/документация обновлены (при изменениях API, скриптов).
- Комментарии/decision logs там, где логика нетривиальна.

# PulsePlate Technical Guidelines

## 📋 Правила кодирования для PulsePlate

### Python (Backend)

- **Формат**: Black, line-length=100
- **Типы**: Type hints обязательны для всех функций
- **Pydantic**: Используй v2 APIs (`model_dump()`, `model_validate()`)
- **Тесты**: 97% coverage requirement, используй Bayesian diagnostics
- **Стиль**: PEP 8, комментарии на русском и английском

### Swift (iOS Frontend)

- **Стиль**: Apple Human Interface Guidelines
- **Accessibility**: AA уровень (VoiceOver, Dynamic Type, контрастность)
- **Локализация**: RU/EN/ES поддержка
- **Дизайн**: Минимализм, доверие, научность + геймификация

### Тестирование

- **Покрытие**: Diff coverage ≥97% на изменённых строках
- **Bayesian analysis**: Используй Bayesian диагностику для анализа тестов
- **Моки**: По модулям/функциям, не по классам (thin slices approach)
- **Интеграция**: Вертикальные тесты (API→UI→тесты→i18n→a11y)

### Архитектура

- **Чистая архитектура**: Разделение слоёв, зависимости внутрь
- **Feature flags**: VIP модули за флагами
- **OpenAPI**: Source-of-truth для типов и моков
- **Thin slices**: Полный вертикальный срез в каждом PR

## 🔍 PulsePlate-специфичные технические паттерны

### Bayesian Test Diagnostics

- Используй `pytest_bayesian_plugin.py` для анализа тестов
- Bayesian analyzers для business и nutrition логики
- Safety score tracking для nutrition анализа

### Health Data Validation

- Строгая валидация BMI, калорий, макронутриентов
- Nutrition standards compliance
- Medical safety checks

## 🌐 Философия кодинга PulsePlate

**Принципы разработки:**

- **Thin slices**: каждый PR — полный вертикальный срез (API→UI→тесты→i18n→a11y), ≤600 строк
- **Source-of-truth**: типы и моки генерим из **OpenAPI**
- **Feature flags**: все VIP-модули за `VITE_VIP_MODULE_ENABLED`
- **Diff coverage ≥97%** (по изменённым файлам), не тотальная
- **Design = Trust**: минимализм, читаемость, предсказуемые жесты/переходы
- **Bayesian diagnostics**: использование Bayesian анализа для диагностики тестов

### Код: простой, но мощный

- MVP → рынок → масштаб
- Минимализм без потери функциональности
- Каждый экран ведёт к удержанию и подписке (VIP conversion)

## 📝 Управление версиями

- **Атомарные коммиты**: Одно логическое изменение за коммит
- **Префиксы**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
- **Conventional commits**: `<type>(<scope>): <subject>`
- **Ссылки на задачи**: Упоминай связанные PR/issues

## 💰 Учёт бюджета и эффективности

- **Open-source прежде всего**: Предпочитай открытые библиотеки
- **Минимализм**: MVP подход, не переусложняй
- **Осознанное использование ресурсов**: Эффективность при масштабировании
- **Чёткое указание дат**: Используй точные форматы, часовой пояс `America/New_York`

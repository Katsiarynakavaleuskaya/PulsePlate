# 🧠 Стратегия Расширения Байесовских Методов в PulsePlate

**Версия**: 2.0
**Дата**: 2025-01-09
**Статус**: Strategic Planning

---

## 📊 Текущее Состояние Байесовских Методов

### ✅ Реализовано

1. **BayesianTestAnalyzer** (`core/bayesian_test_analyzer.py`)
   - Диагностика падений тестов с использованием теоремы Байеса
   - Априорные вероятности для типов ошибок
   - Анализ корреляций между тестами
   - История выполнения тестов

2. **NutritionBayesianAnalyzer** (`core/nutrition_bayesian_analyzer.py`)
   - Валидация безопасности питания
   - Обнаружение опасных значений калорий/BMI
   - Проверка баланса макронутриентов
   - Анализ соответствия медицинским стандартам

3. **BusinessBayesianAnalyzer** (`core/business_bayesian_analyzer.py`)
   - Анализ бизнес-логики и монетизации
   - Оптимизация затрат
   - Стратегии роста доходов

4. **ComprehensiveBayesianAnalyzer** (`core/comprehensive_bayesian_analyzer.py`)
   - Комплексный анализ всех аспектов системы
   - Health First политика

5. **A/B Testing** (`docs/AB_TESTING_BAYES.md`)
   - Beta-Bernoulli модель для конверсий
   - Thompson Sampling для VIP/paywall

---

## 🎯 Новые Области Применения

### 1. 🍎 Байесовская Валидация Данных Питания (Приоритет: ВЫСОКИЙ)

**Проблема**: Пользователи могут вводить нереалистичные данные (например, яблоко с 5000 калориями).

**Решение**: Байесовский валидатор, который:

- Использует популяционные данные как prior
- Учитывает историю пользователя как likelihood
- Вычисляет posterior вероятность реалистичности

**Уникальность**:

- Адаптивная валидация, которая учится на поведении конкретного пользователя
- Не блокирует, а предлагает исправления с уверенностью

**Файл**: `core/bayesian/nutrition_data_validator.py`

**Интеграция**:

- Эндпоинт `/api/validate_meal` перед сохранением данных
- UI показывает предупреждения с уровнем уверенности

**Ожидаемый эффект**:

- ⚡ Снижение аномальных данных на 40%
- 🎯 Улучшение качества данных на 30%

---

### 2. 👤 Байесовский Анализатор Поведения Пользователей (Приоритет: ВЫСОКИЙ)

**Проблема**: Нужно предсказывать churn, engagement, достижение целей.

**Решение**: Многоуровневая байесовская модель:

- **Hierarchical Bayesian Model** для учета индивидуальных различий
- **Beta-Bernoulli** для бинарных событий (churn, goal achievement)
- **Gaussian Process** для временных рядов (тренды активности)

**Уникальность**:

- Учитывает неопределенность для новых пользователей (использует популяционные priors)
- Адаптируется к каждому пользователю по мере накопления данных
- Предсказывает не только вероятность, но и уверенность

**Файл**: `core/bayesian/user_behavior_analyzer.py`

**Методы**:

```python
- predict_churn_risk(user_id) -> BayesianPrediction
- predict_goal_achievement_probability(user_id, goal_type) -> BayesianPrediction
- predict_optimal_notification_time(user_id) -> BayesianPrediction
- predict_meal_preference(user_id, meal_options) -> Dict[str, float]
```

**Интеграция**:

- Фоновый джоб для вычисления рисков churn
- Персонализированные уведомления в оптимальное время
- Ранжирование блюд по вероятности выбора

**Ожидаемый эффект**:

- 📈 Увеличение retention на 15-20%
- 🎯 Улучшение точности предсказаний на 25-30%

---

### 3. 🎯 Адаптивная Система Рекомендаций (Приоритет: СРЕДНИЙ)

**Проблема**: Статические рекомендации не учитывают feedback пользователей.

**Решение**: **Thompson Sampling Multi-Armed Bandit**:

- Каждая стратегия рекомендации = "arm"
- Балансирует exploration (пробовать новое) vs exploitation (использовать лучшее)
- Обновляется в реальном времени на основе feedback

**Уникальность**:

- Не требует A/B тестов заранее: алгоритм учится автоматически и адаптируется к изменениям предпочтений пользователя.
- Учитывает контекст (время суток, сезонность, цели).

**Файл**: `core/bayesian/adaptive_recommender.py`

**Стратегии**:

- High protein focus
- Balanced macros
- Low carb
- Mediterranean style
- Weight loss optimized
- Muscle gain optimized

**Интеграция**:

- Использует `core/recommendations.py` как точку расширения рекомендаций.
- Обновляет веса на основе кликов и игнорирования.
- Персонализирует выдачу для каждого пользователя.

**Ожидаемый эффект**:

- 🎯 Улучшение CTR рекомендаций на 30-40%
- 💡 Увеличение удовлетворенности пользователей на 15%

---

### 4. 🔍 Байесовское Обнаружение Аномалий Здоровья (Приоритет: ВЫСОКИЙ)

**Проблема**: Раннее обнаружение проблем со здоровьем (недоедание, переедание, дефициты).

**Решение**: **Bayesian Change Point Detection**:

- Обнаруживает изменения в паттернах питания.
- Использует prior-знания о нормальных паттернах.
- Вычисляет вероятность того, что изменение значимо.

**Уникальность**:

- Не требует жестких порогов: использует вероятностный подход и учитывает естественную вариативность пользователя.
- Предупреждает о проблемах до того, как они станут критическими.

**Файл**: `core/bayesian/health_anomaly_detector.py`

**Методы**:

```python
- detect_calorie_pattern_change(user_id, days=7) -> BayesianPrediction
- detect_nutrient_deficiency_risk(user_id, nutrient) -> BayesianPrediction
- detect_eating_disorder_risk(user_id) -> BayesianPrediction
```

**Интеграция**:

- Еженедельный анализ для всех активных пользователей
- Автоматические предупреждения в приложении
- Интеграция с системой уведомлений

**Ожидаемый эффект**:

- 🔍 Раннее обнаружение проблем на 2-3 недели раньше
- 💚 Улучшение здоровья пользователей на 20%

---

### 5. 📊 Байесовская Оптимизация API Производительности (Приоритет: СРЕДНИЙ)

**Проблема**: Нужно оптимизировать кэширование, батчинг, предзагрузку данных.

**Решение**: **Bayesian Optimization** (Gaussian Process):

- Оптимизирует гиперпараметры (TTL кэша, размер батча) и учитывает неопределенность измерений.
- Балансирует exploration и exploitation.

**Уникальность**:

- Автоматически оптимизирует параметры без ручного тюнинга, учитывает изменяющиеся паттерны нагрузки и минимизирует количество экспериментов.

**Файл**: `core/bayesian/api_performance_optimizer.py`

**Параметры для оптимизации**:

- TTL кэша для разных типов данных
- Размер батча для bulk операций
- Приоритеты предзагрузки данных
- Стратегии инвалидации кэша

**Ожидаемый эффект**:

- ⚡ Снижение времени отклика API на 20-30%
- 💰 Снижение затрат на инфраструктуру на 15%

---

### 6. 🎨 Байесовская Персонализация UI/UX (Приоритет: НИЗКИЙ)

**Проблема**: Разные пользователи предпочитают разные интерфейсы.

**Решение**: **Contextual Bandits**:

- Рассматривает разные варианты UI как arms, учитывает контекст пользователя (опыт, цели, устройство) и обновляется на основе взаимодействий.

**Уникальность**:

- Персонализирует не только контент, но и интерфейс, учитывает контекст использования и автоматически адаптируется без ручной настройки.

**Файл**: `core/bayesian/ui_personalizer.py`

**Варианты для тестирования**:

- Расположение элементов навигации
- Стиль графиков и визуализаций
- Частота уведомлений
- Тип мотивационных сообщений

**Ожидаемый эффект**:

- 📱 Улучшение engagement на 10-15%
- ⏱️ Снижение времени на выполнение задач на 20%

---

### 7. 🏥 Байесовская Диагностика Проблем Питания (Приоритет: ВЫСОКИЙ)

**Проблема**: Нужно диагностировать причины проблем с питанием (дефициты, дисбалансы).

**Решение**: **Bayesian Network**:

- Моделирует причинно-следственные связи, учитывает неопределенность в данных и предоставляет объяснимые диагнозы.

**Уникальность**:

- Объяснимый AI: показывает причинно-следственные связи и одновременно учитывает множественные факторы.
- Предоставляет вероятностные диагнозы с уверенностью

**Файл**: `core/bayesian/nutrition_diagnostic_engine.py`

**Диагностируемые проблемы**:

- Дефицит микронутриентов
- Дисбаланс макронутриентов
- Недостаточное потребление калорий
- Избыточное потребление калорий
- Проблемы с гидратацией

**Интеграция**:

- Интеграция с модулем `core/recommendations.py`
- Автоматические рекомендации по исправлению
- Визуализация причинно-следственных связей

**Ожидаемый эффект**:

- 🎯 Улучшение точности диагностики на 35%
- 💡 Улучшение понимания пользователями своих проблем

---

### 8. 📈 Байесовское Прогнозирование Прогресса (Приоритет: СРЕДНИЙ)

**Проблема**: Пользователи хотят знать, когда достигнут целей.

**Решение**: **Bayesian Linear Regression** с неопределенностью:

- Предсказывает прогресс с учетом неопределенности
- Учитывает историю пользователя и обновляется по мере поступления новых данных

**Уникальность**:

- Показывает не только прогноз, но и диапазон неопределенности
- Адаптируется к изменениям в поведении
- Учитывает естественную вариативность

**Файл**: `core/bayesian/progress_predictor.py`

**Прогнозируемые метрики**:

- Достижение целевого веса
- Достижение целевых макронутриентов
- Улучшение показателей здоровья

**Интеграция**:

- Виджет прогноза в дашборде пользователя
- Мотивационные сообщения на основе прогноза
- Адаптация целей на основе прогноза

**Ожидаемый эффект**:

- 📈 Улучшение мотивации пользователей на 25%
- 🎯 Увеличение достижения целей на 20%

---

## 🔧 Расширения Существующих Методов

### 1. Улучшение BayesianTestAnalyzer

**Текущие ограничения**:

- Статические априорные вероятности
- Не учитывает контекст проекта

**Улучшения**:

1. **Adaptive Priors**: Обновление priors на основе истории проекта
2. **Context-Aware Diagnosis**: Учет типа проекта, технологий, команды
3. **Multi-Level Hierarchical Model**: Учет зависимостей между тестами
4. **Uncertainty Quantification**: Показ уверенности в диагнозах

**Файл**: `core/bayesian_test_analyzer.py` (расширение)

---

### 2. Расширение NutritionBayesianAnalyzer

**Текущие ограничения**:

- Только статические проверки
- Не учитывает индивидуальные особенности

**Улучшения**:

1. **Personalized Safety Thresholds**: Адаптация порогов под пользователя
2. **Temporal Pattern Analysis**: Анализ паттернов во времени
3. **Multi-Nutrient Interactions**: Учет взаимодействий между нутриентами
4. **Disease Risk Prediction**: Предсказание рисков заболеваний

**Файл**: `core/nutrition_bayesian_analyzer.py` (расширение)

---

### 3. Улучшение A/B Testing

**Текущие ограничения**:

- Простая Beta-Bernoulli модель
- Не учитывает контекст

**Улучшения**:

1. **Contextual Bandits**: Учет контекста пользователя
2. **Multi-Armed Bandits**: Оптимизация нескольких вариантов одновременно
3. **Non-Stationary Bandits**: Адаптация к изменениям во времени
4. **Safety Constraints**: Гарантии безопасности для критических метрик

**Файл**: `core/bayesian/advanced_ab_testing.py` (новый)

---

## 🎨 Уникальные Фичи для PulsePlate

### 1. Байесовская Система Объяснений (Explainable AI)

**Цель**: Пользователи хотят понимать, почему система дает определенные рекомендации.

**Решение**:

- Генерация объяснений на основе байесовских вероятностей
- Показ влияния различных факторов
- Визуализация причинно-следственных связей

**Файл**: `core/bayesian/explanation_generator.py`

**Примеры объяснений**:

- "Мы рекомендуем увеличить белок на 20г, потому что ваша история показывает, что это улучшит достижение целей на 85%"
- "Риск дефицита витамина D составляет 65% на основе ваших данных за последние 2 недели"

---

### 2. Байесовская Система Доверия (Trust Score)

**Цель**: Пользователи должны доверять системе.

**Решение**:

- Вычисление "доверия" к системе на основе точности предсказаний
- Показ уверенности в рекомендациях
- Адаптация уровня детализации объяснений

**Файл**: `core/bayesian/trust_scorer.py`

**Метрики доверия**:

- Точность предсказаний для пользователя
- Консистентность рекомендаций
- Успешность достижения целей

---

### 3. Байесовская Система Обучения (Meta-Learning)

**Цель**: Система должна учиться на опыте всех пользователей.

**Решение**:

- **Hierarchical Bayesian Models**: Обучение на популяционном уровне
- **Transfer Learning**: Перенос знаний между похожими пользователями
- **Few-Shot Learning**: Быстрая адаптация к новым пользователям

**Файл**: `core/bayesian/meta_learner.py`

**Преимущества**:

- Новые пользователи получают лучшие рекомендации сразу
- Система улучшается со временем автоматически
- Учет редких случаев через популяционные данные

---

## 📋 План Внедрения (Приоритизированный)

### Phase 1: Quick Wins (2-3 недели)

1. ✅ Байесовская валидация данных питания
2. ✅ Байесовское обнаружение аномалий здоровья
3. ✅ Улучшение BayesianTestAnalyzer с адаптивными priors

### Phase 2: Core Features (4-6 недель)

4. ✅ Байесовский анализатор поведения пользователей
5. ✅ Байесовская диагностика проблем питания
6. ✅ Расширение NutritionBayesianAnalyzer

### Phase 3: Advanced Features (6-8 недель)

7. ✅ Адаптивная система рекомендаций
8. ✅ Байесовское прогнозирование прогресса
9. ✅ Байесовская система объяснений

### Phase 4: Optimization (4-6 недель)

10. ✅ Байесовская оптимизация API
11. ✅ Улучшение A/B тестирования
12. ✅ Байесовская система доверия

### Phase 5: Meta-Learning (6-8 недель)

13. ✅ Байесовская система обучения
14. ✅ Байесовская персонализация UI/UX

---

## 🎯 Метрики Успеха

### Технические Метрики

- **Точность предсказаний**: > 85%
- **Время отклика**: < 100ms для валидации
- **Покрытие тестами**: > 90%
- **Ложные срабатывания**: < 5%

### Бизнес Метрики

- **User Retention**: +20-25%
- **Точность рекомендаций**: +30-40%
- **Аномальные данные**: -40-50%
- **User Satisfaction**: +15-20%
- **Достижение целей**: +20-25%

### Уникальность

- **Первый в индустрии**: Байесовская система объяснений для питания
- **Уникальная фича**: Адаптивная валидация данных
- **Конкурентное преимущество**: Meta-learning для быстрой адаптации

---

## 🚀 Следующие Шаги

1. **Создать ветку**: `feat/bayesian-expansion`
2. **Начать с Phase 1**: Quick Wins
3. **Создать базовую архитектуру**: `core/bayesian/` модуль
4. **Интегрировать с существующими системами**
5. **Мониторинг и метрики**: Prometheus/Grafana дашборды

---

## 📚 Ресурсы

### Библиотеки

- `numpy` - базовые математические операции
- `scipy` - статистические распределения
- `pymc3` или `pymc4` (optional) - продвинутые байесовские модели
- `scikit-learn` - базовые ML алгоритмы

### Документация

- [Bayesian Data Analysis](http://www.stat.columbia.edu/~gelman/book/)
- [Thompson Sampling Tutorial](https://web.stanford.edu/~bvr/pubs/TS_Tutorial.pdf)
- [Multi-Armed Bandits](https://arxiv.org/abs/1904.07272)
- [Hierarchical Bayesian Models](https://www.stat.columbia.edu/~gelman/research/published/stan_jebs_2.pdf)

---

**Статус**: ✅ Стратегия готова к реализации
**Следующий шаг**: Начать с Phase 1, Quick Wins

---

## 🔁 Подробное Дорожное Планирование (добавления к стратегии)

Ниже — детализированные этапы, согласованные для практической реализации. Они дополняют и конкретизируют существующие Phases в этом документе.

### PHASE 0: Инфраструктура (1 неделя) – подготовка данных и окружения

- Обновить зависимости: добавить `numpy`, `scipy` в `requirements.txt` (и при необходимости в `requirements-dev.txt`)
- Создать модуль `core/bayesian/` (базовые структуры, схемы данных, utils)
- Расширить модели данных для сбора обратной связи:
  - `RecommendationFeedback` (user_id, recommendation_id, context, chosen:boolean, timestamp)
  - `MealEntry`/`NutritionEntry` (нормализованный ввод питания)
- Миграции Alembic для новых таблиц (feedback, telemetry)
- Базовые тесты (включая миграции и схемы)
- Метрики и базовые дашборды (Prometheus/Grafana заготовка)

#### Assumptions & Requirements

- Team & headcount (approx FTEs for Phase 0):
  - DS/ML: 0.5 FTE; ML Engineer: 0.5 FTE; Backend (FastAPI): 0.5 FTE
  - iOS (SwiftUI): 0.25 FTE; DevOps/SRE: 0.25 FTE; QA: 0.25 FTE
  - Data Engineer (optional): 0.25 FTE (if needed for data pipelines)
- External data sources and access:
  - USDA FoodData Central API: API key provisioned. If not, +1–3 days
  - OpenFoodFacts (optional import/API): If used, +1–2 days
  - WHO/FAO nutrient reference tables (static): If not available, +0.5 day
- Database baseline (dev/staging for Phase 0):
  - Postgres 14+ with pooling (pgBouncer) or SQLite for local dev
  - Validation endpoint load: 50–100 RPS; p95 < 50 ms
  - Initial storage: 5–10 GB (food catalog + telemetry), daily growth < 200 MB
  - If DB or pooling not provisioned, +2–3 days
- Third‑party services to provision:
  - Monitoring/metrics: Prometheus + Grafana dashboards. If absent, +2 days
  - Error tracking: Sentry. If absent, +0.5 day
  - Task queue: Redis + TaskIQ/Celery for batch jobs. If absent, +1–2 days
  - CI/CD (GitHub Actions + secrets): assumed ready. If not, +1–2 days

Ожидаемый результат: технически готовая база для фаз 1–2 (хранилище, библиотеки, каркас).

---

### PHASE 1: Quick Wins (2–3 недели) 🚀

#### Приоритет 1: Байесовская Валидация Данных

- ✅ Реализовать `NutritionDataValidator` (использовать популяционные priors + история пользователя)
- ✅ Интегрировать в endpoint `/api/validate_meal`
- ✅ UI показывает предупреждения (warnings) с указанием уверенности и пояснениями
- ✅ Использовать данные USDA как prior (нормы/эталонные значения)
- ✅ Протестировать edge-cases (например, «яблоко 5000 kcal») — property-based (Hypothesis)

#### Приоритет 2: Адаптивные Рекомендации (Thompson Sampling)

- ✅ Расширить `core/recommendations.py` адаптивным слоем (arms = стратегии)
- ✅ Добавить A/B тестирование стратегий
- ✅ Интегрировать в существующие endpoints
- ✅ Хранить feedback (выбор/игнор) в БД
- ✅ Dashboard для мониторинга: какие стратегии работают, CTR по arms, конверсия

Ожидаемые результаты:

- 📊 Снижение аномальных данных на 40%
- 🎯 Улучшение CTR рекомендаций на 20–30%

#### Measurement Plan (План измерений)

- **Базовые значения (до запуска эксперимента)**:
  - **CTR_baseline (рекомендации)**: средний CTR за последние 14 календарных дней до T0 (дата старта эксперимента). Зафиксировать значение в дашборде/логе: `CTR_baseline_14d = X.XX%`.
  - **AnomalyRate_baseline (валидация питания)**: доля аномальных/подозрительных записей в питании за последние 30 календарных дней до T0. Зафиксировать: `AnomalyRate_baseline_30d = Y.YY%`.
  - Источники данных и окна измерения зафиксировать в описании отчёта (Prometheus/Grafana + выгрузка в репозиторий отчетов).
- **Порог успеха (чёткие целевые значения)**:
  - Перейти к Phase 2, если одновременно:
    - **CTR_lift ≥ +20% (relative)** относительно `CTR_baseline_14d`, и
    - **AnomalyRate_reduction ≥ −40% (relative)** относительно `AnomalyRate_baseline_30d`.
  - Доп. охранные метрики (guardrails): отсутствие деградации стабильности сервиса и UX (латентность API p95 не ухудшилась >10%, рост ошибок валидации/крашей = 0 по сравнению с контролем).
- **Дизайн эксперимента**:
  - **Метод**: A/B‑тест на уровне пользователя (рандомизация 50/50, постоянное закрепление пользователя за вариантом).
  - **Группы**: Control = текущая логика; Treatment = Phase 1 (валидатор + адаптивные рекомендации).
  - **Размер выборки**: минимум `n = 5 000` уникальных пользователей на группу.
  - **Длительность**: 14 календарных дней (не менее 2 полных недельных циклов).
  - **Статпараметры**: целевая мощность 80%, α = 0.05; фиксированный горизонт без «peeking», одна промежуточная проверка на 7‑й день для правил остановки/отката.
- **Отчётные метрики и статистика**:
  - **CTR** по группам: среднее значение, **95% CI**, относительный lift (%), **p‑value** (двусторонний тест пропорций).
  - **Anomaly rate** по группам: среднее значение, **95% CI**, относительное снижение (%), **p‑value**.
  - Приложить графики кумулятивного эффекта и стабильности метрик по дням.
- **Go/No‑Go и правила отката**:
  - **Go**: оба целевые пороги достигнуты (CTR_lift ≥ 20%, AnomalyRate_reduction ≥ 40%), 95% CI для разницы не включает 0, p‑value < 0.05, guardrails соблюдены → масштабируем Treatment и переходим к Phase 2.
  - **No‑Go**: один из порогов не достигнут или статистическая значимость отсутствует → итерация Phase 1 (улучшения/фиксы) и повторный эксперимент.
  - **Early rollback (промежуточная проверка на 7‑й день)**: немедленный откат фич (feature‑flag OFF) при любом из условий:
    - рост доли аномалий в Treatment > 10% относительно контроля или базовой линии,
    - падение CTR в Treatment ≥ 5% относительно контроля,
    - существенные регрессы по стабильности (латентность p95 > +15% к контролю, рост ошибок).
  - Откат выполняется через feature‑flag; результаты фиксируются в отчёте, причины и действия — в changelog эксперимента.

---

### PHASE 2: Обнаружение Аномалий (3–4 недели) 🔍

#### Приоритет 1: Simple Change Point Detection

- ✅ Реализовать `HealthAnomalyDetector` (изменения в паттернах питания/логирования)
- ✅ Еженедельный анализ активных пользователей (batch job)
- ✅ Автоматические уведомления (асинхронная очередь)
- ✅ Dashboard для врачей/нутрициологов (агрегаты, heatmaps, тревоги)

#### Приоритет 2: Nutrient Deficiency Risk

- ✅ Анализ дефицитов на основе недельных данных (постериоры по нутриентам)
- ✅ Интеграция с существующими рекомендациями (food-first approach)

Ожидаемые результаты:

- 🔍 Раннее обнаружение проблем на 1–2 недели
- 💚 Улучшение удовлетворённости пользователей

---

### PHASE 3: Предсказательная Аналитика (4–6 недель) 📈

Предпосылки к началу:

- ✅ 1–2 месяца данных пользователей
- ✅ Обученные prior-распределения
- ✅ Понимание ключевых паттернов по сегментам

Задачи:

- ✅ Упрощённый Байесовский анализатор поведения
- ✅ Прогнозирование достижения целей (с неопределённостью)
- ✅ Персонализация уведомлений (оптимальное время, частота)

---

### PHASE 4: Explainable AI (3–4 недели) 🎨

Задачи и критерии качества:

- ✅ Определение стандарта «валидного объяснения»:
  - Текст объяснения должен:
    1) указывать топ‑3 наиболее влиятельных фактора,
    2) приводить их posterior‑вероятности и доверительные интервалы (confidence bands),
    3) явно обозначать направление влияния (усиливает/ослабляет),
    4) содержать краткую причинно‑следственную цепочку.
  - Пример формата: «Белок ниже личной нормы на 18% (P=0.82, CI95% [0.74, 0.88]) → повышает риск срыва диеты (P=0.69). Рекомендуем увеличить белок на 20 г».
- ✅ Валидация точности объяснений:
  - Unit‑тесты логики генерации объяснений (детерминированные фикстуры → воспроизводимые posterior/CI).
  - Экспертный обзор (нутрициологи/медицинские консультанты) по чек‑листу раз в неделю; метрика согласия экспертов ≥ 80%.
  - Небольшое пользовательское исследование (A/B + опрос): субъективная понятность ≥ 75%, полезность ≥ 70%; фидбек циклически встраивается (feedback loop).
- ✅ Визуализация причинно‑следственных связей:
  - Подход: интерактивная визуализация Bayesian Network (D3.js или Sigma.js/Vis.js).
  - Отображение неопределенности:
    - толщина/прозрачность ребра ∝ силе/уверенности,
    - цвет узла по направлению эффекта,
    - tooltips с posterior и CI.
  - Взаимодействия: раскрытие/сворачивание подграфов, подсветка путей влияния, экспорт в PNG/SVG.
- ✅ Политика обработки «удивительных/тревожных» объяснений:
  - При низкой уверенности (например, P < 0.6) объяснение помечается как «низкая уверенность», добавляются caveats и ссылка «Сообщить о проблеме».
  - Авто‑эскалация в журнал QA/мед. обзор при потенциально вредных интерпретациях; блокировка использования таких объяснений в критических сценариях до подтверждения.
  - Все объяснения логируются для аудита и ретроспективного анализа дрейфа.

Подэтапы и результаты:

- 4a. Базовые текстовые объяснения (высокая уверенность) + логирование
  - Deliverables:
    - Сервис генерации текстовых объяснений (API) с топ‑факторами, posterior и CI.
    - Полное логирование (объяснение, входные признаки, версии моделей, метаданные).
    - Unit‑тесты детерминированных кейсов; база примеров для регрессии.
  - Успех:
    - ≥ 95% объяснений проходят sanity‑checks на непротиворечивость.
    - Согласие экспертов по чек‑листу ≥ 80%; жалобы пользователей < 2%.
- 4b. Интерактивные визуализации + UX‑валидация
  - Deliverables:
    - Веб‑компонент визуализации Bayesian Network (D3/Sigma/Vis) с рендерами неопределенности.
    - UX‑тестирование с 10–20 пользователями, итерации по результатам.
    - Включение фичи под feature‑flag; мониторинг метрик понятности/полезности.
  - Успех:
    - Понятность объяснений (опрос) ≥ 80%; улучшение NPS объяснений ≥ +10 п.п.
    - Отсутствие критических инцидентов из‑за неверных трактовок.

---

### PHASE 5: Advanced Topics (6–8 недель) 🚀

Только после накопления достаточного объёма данных:

- ✅ Hierarchical Bayesian Models (учёт межпользовательской вариативности)
- ✅ Meta-Learning / Transfer Learning
- ✅ Байесовские нейросети (по необходимости)

---

## 🎨 Уникальные фичи для PulsePlate (усиливают дифференциацию)

### 1. Bayesian Health Coach 💡

Персональный AI-коуч, который:

- Адаптируется к стилю питания пользователя
- Предсказывает предпочтения и объясняет рекомендации с уверенностью
- Показывает прогресс с доверительными интервалами (uncertainty bands)

API-эскиз:

```python
from typing import Optional
from datetime import datetime


class BayesianHealthCoach:
    def get_daily_insight(self, user_id: int, timeout_ms: int = 90) -> Optional["Insight"]:
        """
        RU: Быстрый пользовательский вызов с ограничением по времени.
            - SLA: p95 < 90–120 мс на проде; по умолчанию timeout_ms=90.
            - При истечении таймаута:
                1) Возвращает кэшированный результат, если он «свежий» (например, TTL ≤ 6–12 часов),
                2) Иначе возвращает None (клиент показывает дружелюбное сообщение и/или skeleton UI).
            - Ошибки вычисления логируются; триггерится фоновая задача на пересчёт.
        EN: Fast user-facing call with strict timeout.
            - SLA: p95 < 90–120 ms in production; default timeout_ms=90.
            - On timeout:
                1) Return cached result if fresh (e.g., TTL ≤ 6–12h),
                2) Else return None (client shows friendly message and/or skeleton UI).
            - Failures are logged; a background recompute job is enqueued.
        """
        # Fast-path: try fresh cache first
        cached = self._get_cached_insight(user_id)
        if cached and self._is_fresh(cached):
            return cached

        # Start bounded computation
        try:
            return self._compute_insight_bounded(user_id=user_id, timeout_ms=timeout_ms)
        except TimeoutError:
            # Fallback to stale cache if acceptable, else None
            if cached:
                return cached  # degraded-but-usable
            return None
        except Exception:
            self._log_error("daily_insight_failed", user_id=user_id)
            self._enqueue_background_recompute(user_id)
            return cached or None

    def get_detailed_insight(self, user_id: int, as_of: Optional[datetime] = None) -> "Insight":
        """
        RU: Подробный расчёт без таймаута для фоновой обработки/офлайна.
            - Используется при логине/ночных задачах/ручном пересчёте.
            - Возвращает полный Insight с расширенными полями и метаданными модели.
        EN: Detailed, no-timeout computation for background/offline processing.
            - Used at login/nightly jobs/manual rebuild.
            - Returns full Insight with extended fields and model metadata.
        """
        return self._compute_insight_full(user_id=user_id, as_of=as_of or datetime.utcnow())
```

Контракт и SLA:

- Быстрый вызов (UI): p95 < 90–120 мс; `timeout_ms` по умолчанию 90. При таймауте — кэш или `None`.
- Фоновый вызов (без таймаута): запускается системой; не используется напрямую в UI.

Семантика вызова (invocation semantics):

- On‑demand: пользователь открывает экран/тянет refresh → `get_daily_insight(...)`.
- On‑login (lazy precompute): после успешного входа ставим задачу `get_detailed_insight(...)` для обновления кэша.
- Scheduled/background: ночной батч (напр. 02:00) пересчитывает `get_detailed_insight(...)` для активных пользователей.

Фолбэк и ошибки:

- Недостаточно данных → возвращаем кэш (если есть) либо `None`. Клиент показывает мягкое сообщение: «Недостаточно данных, собираем для точного совета».
- Ошибка/таймаут → логирование (Sentry), метка `status="degraded"` в Insight (если кэш), постановка фоновой задачи.
- Возврат типов:
  - Быстрый метод: `Optional[Insight]` (может быть `None`).
  - Детальный метод: всегда `Insight` (при фатальной ошибке — исключение в фоне с ретраями).

Версионирование и схема Insight (backward‑compatible):

- Версии по SemVer: `schema_version` (формат/поля), `model_version` (версия байесовской модели), `api_contract_version`.
- Старые клиенты: читают только известные поля; новые поля добавляются опционально.
- Миграции:
  - В storage сохраняем `schema_version` на запись.
  - При чтении старых версий применяем адаптеры (upcast) до актуальной схемы.

Пример схемы Insight:

```python
from typing import List, Optional, Literal, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class Insight(BaseModel):
    # Versioning / contracts
    schema_version: str = Field(default="1.0.0", description="SemVer of Insight schema")
    api_contract_version: str = Field(default="1.0.0", description="SemVer of API contract")
    model_version: str = Field(default="bayes-coach-2025.01", description="Model build/version")
    schema_id: Literal["Insight.v1"] = "Insight.v1"

    # Core payload
    insight_id: str
    message: str
    patterns: List[str]
    recommendations: List[str]
    confidence_level: Literal["low", "medium", "high"]

    # Metadata
    generated_at: datetime
    expires_at: Optional[datetime] = None
    status: Literal["fresh", "stale", "degraded"] = "fresh"
    debug: Optional[Dict[str, str]] = None  # optional, stripped in prod responses
```

### 2. Uncertainty Visualization 📊

Показываем прогноз + уверенность:

```json
{
  "predicted_weight_in_30_days": {
    "mean": 72.5,
    "confidence_interval_95": [70.2, 74.8],
    "probability_of_goal": 0.85,
    "explanation": "С вероятностью 85% вы достигнете цели 70кг за 30 дней"
  }
}
```

#### Uncertainty Communication Strategy

- **1) Как считаем интервалы неопределенности**
  - Используем байесовские достоверностные интервалы (credible intervals), рассчитанные из постериорных распределений.
  - Источник: либо семплы постериора (MCMC/бутстрэп/Thompson draws), либо квантильные функции закрытой формы, если распределение задано аналитически.
  - Значения:
    - Медиана: 50‑й перцентиль постериора.
    - 50% диапазон: [25‑й, 75‑й] перцентили.
    - 95% диапазон: [2.5‑й, 97.5‑й] перцентили.
  - Для сильно скошенных распределений допускается HPD‑интервал (Highest Posterior Density). По умолчанию используем перцентильные интервалы ради стабильности и простоты объяснения.
  - Вероятность достижения цели: доля постериорных семплов, удовлетворяющих целевому условию (например, P[weight ≤ goal]).

- **2) Визуальный стиль (UX/UI)**
  - Линия медианы: сплошная, цвет Navy `#0F172A`.
  - 50% интервал: полупрозрачная заливка Blue `#339FFF` (насыщенная).
  - 95% интервал: более светлая заливка Blue `#339FFF` (пониженная непрозрачность).
  - Контраст и доступность: соответствует Apple HIG, поддержка Dynamic Type; проверяем контраст ≥ WCAG AA в светлой/тёмной теме.
  - Tooltip/hover:
    - Показывает: медиану, 50% CI, 95% CI, вероятность достижения цели (если релевантно).
    - Формат: «Медиана: {x}; 50% CI: [{l50}, {u50}]; 95% CI: [{l95}, {u95}]; P(goal)={p}.»
  - VoiceOver/Accessibility Label:
    - «Прогноз с медианой {x}, 50‑процентный интервал {l50}–{u50}, 95‑процентный интервал {l95}–{u95}, вероятность достижения цели {p}%.»

- **3) Горизонт‑зависимая неопределенность**
  - Принцип: чем дальше горизонт прогноза, тем шире интервалы (рост дисперсии).
  - Визуально: ширина 50%/95% полос увеличивается вдоль оси времени; линия медианы остаётся сплошной.
  - Примеры сравнения:
    - 7 дней: «Оценка более уверенная: 95% CI ±0.8 от медианы».
    - 30 дней: «Оценка менее уверенная: 95% CI ±2.3 от медианы».
  - Правило точности: запрещено визуально «сжимать» дальний горизонт; не обрезаем шкалу так, чтобы скрывать рост неопределенности.

- **4) Шаблоны пользовательских формулировок**
  - 50%/95% интервалы:
    - RU: «Медианный прогноз: {x}. 50% интервал: [{l50}, {u50}]. 95% интервал: [{l95}, {u95}].»
    - EN: «Median forecast: {x}. 50% interval: [{l50}, {u50}]. 95% interval: [{l95}, {u95}].»
  - Вероятность достижения цели:
    - Высокая уверенность (P ≥ 0.80)
      - RU: «С вероятностью ~{p}% вы достигнете цели к {horizon}.»
      - EN: «With ~{p}% probability you will reach the goal by {horizon}.»
    - Умеренная (0.60 ≤ P < 0.80)
      - RU: «Есть хорошая вероятность (~{p}%) достичь цели к {horizon}.»
      - EN: «There is a good chance (~{p}%) to reach the goal by {horizon}.»
    - Неопределённая (0.40 ≤ P < 0.60)
      - RU: «Прогноз неопределён: шансы около {p}%.»
      - EN: «Forecast is uncertain: chances are around {p}%.»
    - Низкая (P < 0.40)
      - RU: «Низкая вероятность (~{p}%) достичь цели к {horizon}.»
      - EN: «Low probability (~{p}%) to reach the goal by {horizon}.»

- **5) Правила fallback‑сообщений**
  - «Слишком рано для прогноза»:
    - Истории меньше N дней (по умолчанию N=7) ИЛИ эффективное число постериорных семплов < 100 ИЛИ относительная ширина 95% CI > 100% медианы.
    - RU: «Недостаточно данных для надёжного прогноза. Пожалуйста, добавьте ещё записи в течение {needed_days} дней.»
    - EN: «Not enough data for a reliable forecast. Please log data for {needed_days} more days.»
  - «Широкий интервал, но показываем»:
    - Если 95% CI очень широк (например, ширина > 60% медианы), отображаем полосы как есть + бейдж «Низкая уверенность», добавляем подсказку о шагах, которые сузят интервал (регулярность логирования, стабильность режима).
  - Рекомендация переоценки:
    - Предлагаем «Переоценить через {k} дней» при появлении новых данных/изменении режима.
    - Если P(goal) в «серой зоне» [0.45, 0.55], явно предлагаем собрать больше данных и пересчитать.

### 3. Adaptive Safety Thresholds 🛡️

Персональные безопасные границы на основе вашей истории (Bayesian baseline) с учётом:

- робастной оценки базового уровня (mitigation выбросов: trimming/median/MAD);
- абсолютных защитных границ MIN_SAFE_FLOOR и MAX_SAFE_CEILING (safety > personalization);
- аудита/объяснимости: запись причин, что повлияло на итоговые границы (baseline vs clamp, какие выбросы удалены).

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, List, Tuple, TypedDict


class BaselineOutlierReport(TypedDict, total=False):
    """Структура отчёта об удалённых выбросах. EN: Outlier removal summary."""

    method: str
    removed_count: int
    notes: str


@dataclass
class Limits:
    """Итоговые безопасные границы. EN: Final personalised safety envelope."""

    min_safe: float
    max_safe: float
    confidence: float
    message: str
    rationale: str


class PersonalizedSafetyLimits:
    # RU: Значения-заглушки, NFR — требуется утверждение клинико‑нутриционного совета.
    # EN: Placeholder guardrails — obtain approval via the Medical Safety Workflow (§ Medical Safety Approval Workflow).
    # NOTE: These constants MUST be loaded from config/medical_safety.yaml at runtime.
    # Hardcoded defaults are NOT allowed in production - use None/sentinel values instead.
    # See CONTRIBUTING.md § Medical Safety Approval Workflow for approval requirements.
    MIN_SAFE_FLOOR_KCAL: float | None = None  # Must be loaded from config/medical_safety.yaml
    MAX_SAFE_CEILING_KCAL: float | None = None  # Must be loaded from config/medical_safety.yaml

    # Feature flag: Medical alerts/enforcements are disabled by default until approved
    # Set featureFlags.medicalSafetyApproved = true in config after approval workflow
    _medical_safety_approved: bool = False  # Loaded from config/medical_safety.yaml

    def __init__(self):
        """Initialize with runtime validation of medical safety configuration.

        Raises:
            RuntimeError: If config values are missing, out of range, or approval flag is false
                in production environment. This prevents production use of fallback values.
        """
        import yaml
        from pathlib import Path
        import logging
        import os

        logger = logging.getLogger(__name__)
        config_path = Path("config/medical_safety.yaml")

        # Load configuration
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            error_msg = f"Medical safety config not found: {config_path}"
            logger.error(error_msg)
            if os.getenv("ENVIRONMENT") == "production":
                raise RuntimeError(error_msg + " - Production requires valid config")
            return
        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML in medical safety config: {e}"
            logger.error(error_msg)
            if os.getenv("ENVIRONMENT") == "production":
                raise RuntimeError(error_msg + " - Production requires valid config")
            return

        # Validate and load MIN_SAFE_FLOOR_KCAL
        min_kcal = config.get("MIN_SAFE_FLOOR_KCAL")
        if min_kcal is None:
            error_msg = "MIN_SAFE_FLOOR_KCAL missing from config/medical_safety.yaml"
            logger.error(error_msg)
            if os.getenv("ENVIRONMENT") == "production":
                raise RuntimeError(error_msg + " - Production requires valid config")
            return
        if not isinstance(min_kcal, (int, float)) or not (800 <= min_kcal <= 2000):
            error_msg = f"MIN_SAFE_FLOOR_KCAL out of acceptable range [800, 2000]: {min_kcal}"
            logger.error(error_msg)
            if os.getenv("ENVIRONMENT") == "production":
                raise RuntimeError(error_msg + " - Production requires valid config")
            return
        self.MIN_SAFE_FLOOR_KCAL = float(min_kcal)

        # Validate and load MAX_SAFE_CEILING_KCAL
        max_kcal = config.get("MAX_SAFE_CEILING_KCAL")
        if max_kcal is None:
            error_msg = "MAX_SAFE_CEILING_KCAL missing from config/medical_safety.yaml"
            logger.error(error_msg)
            if os.getenv("ENVIRONMENT") == "production":
                raise RuntimeError(error_msg + " - Production requires valid config")
            return
        if not isinstance(max_kcal, (int, float)) or not (3000 <= max_kcal <= 8000):
            error_msg = f"MAX_SAFE_CEILING_KCAL out of acceptable range [3000, 8000]: {max_kcal}"
            logger.error(error_msg)
            if os.getenv("ENVIRONMENT") == "production":
                raise RuntimeError(error_msg + " - Production requires valid config")
            return
        self.MAX_SAFE_CEILING_KCAL = float(max_kcal)

        # Validate medical safety approval flag
        feature_flags = config.get("featureFlags", {})
        self._medical_safety_approved = feature_flags.get("medicalSafetyApproved", False)

        if os.getenv("ENVIRONMENT") == "production" and not self._medical_safety_approved:
            error_msg = (
                "featureFlags.medicalSafetyApproved is false in production. "
                "Medical safety features require approval before production use."
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info(
            "Medical safety limits loaded: MIN=%s, MAX=%s, Approved=%s",
            self.MIN_SAFE_FLOOR_KCAL,
            self.MAX_SAFE_CEILING_KCAL,
            self._medical_safety_approved,
        )

    def get_calorie_limits(self, user_id: int) -> Limits:
        """Расчёт персональных безопасных границ по истории пользователя."""
        # 1) История пользователя
        user_history: List[float] = self._get_user_history(user_id)  # e.g., список дневных kcal

        # 2) Робастная оценка базового уровня c mitigation выбросов
        #    Robust baseline estimation with outlier mitigation
        baseline_kcal, outlier_info = self._estimate_baseline_robust(user_history)

        # 3) Первичные персональные границы на основе baseline (байесовская усадка опциональна)
        baseline_min: float = baseline_kcal * 0.8
        baseline_max: float = baseline_kcal * 1.3

        # 4) Применение абсолютных защитных границ (safety over personalisation)
        #    Clamp to absolute guardrails
        clamped_min: float = max(baseline_min, self.MIN_SAFE_FLOOR_KCAL)
        clamped_max: float = min(baseline_max, self.MAX_SAFE_CEILING_KCAL)

        # 5) Определение доминирующего правила (baseline vs clamp)
        #    Which rule dominated the final limits
        if clamped_min > baseline_min:
            dominant_rule = "clamp_floor"
        elif clamped_max < baseline_max:
            dominant_rule = "clamp_ceiling"
        else:
            dominant_rule = "baseline"

        # 6) Аудит и объяснение (audit + human‑readable rationale)
        rationale: str = (
            f"Baseline={baseline_kcal:.0f} kcal; "
            f"Initial=[{baseline_min:.0f},{baseline_max:.0f}] -> "
            f"Clamped=[{clamped_min:.0f},{clamped_max:.0f}] "
            f"(rule={dominant_rule}; removed_outliers={outlier_info.get('removed_count', 0)})"
        )
        self._audit_logger.record(
            {
                "user_id": user_id,
                "baseline_method": outlier_info.get("method", "trimmed_median_10pct"),
                "removed_outliers_count": outlier_info.get("removed_count", 0),
                "limits_before_clamp": [baseline_min, baseline_max],
                "limits_after_clamp": [clamped_min, clamped_max],
                "dominant_rule": dominant_rule,
                "rationale": rationale,
            }
        )

        # 7) Возврат рассчитанных границ с сообщением
        return Limits(
            min_safe=clamped_min,
            max_safe=clamped_max,
            confidence=0.9,  # может быть функцией объёма данных/стабильности истории
            message=(
                f"Безопасный диапазон для вас: {clamped_min:.0f}-{clamped_max:.0f} kcal "
                f"(основано на вашей истории; применены защитные границы)."
            ),
            rationale=rationale,  # human‑readable для UI/логов
        )

    def _estimate_baseline_robust(
        self, kcal_values: List[float]
    ) -> Tuple[float, BaselineOutlierReport]:
        """
        RU: Робастная оценка baseline: фильтр невалидных значений, 10%-ое симметричное trimming,
            медиана как устойчивая оценка, отчёт об удалённых выбросах.
        EN: Robust baseline: drop invalids, 10% symmetric trimming, median as robust estimate,
            report removed outliers.
        """
        cleaned: List[float] = [v for v in kcal_values if isinstance(v, (int, float)) and v > 0]
        if not cleaned:
            # Fallback на популяционный prior (пример)
            return 2000.0, BaselineOutlierReport(method="fallback_prior", removed_count=0)
        cleaned.sort()
        n = len(cleaned)
        trim = max(int(0.1 * n), 0)
        trimmed: List[float] = cleaned[trim : n - trim] if n - 2 * trim > 0 else cleaned
        removed_count = n - len(trimmed)
        # Медиана как робастная оценка
        mid = len(trimmed) // 2
        if len(trimmed) % 2 == 1:
            median_val = float(trimmed[mid])
        else:
            median_val = float((trimmed[mid - 1] + trimmed[mid]) / 2.0)
        return median_val, BaselineOutlierReport(
            method="trimmed_median_10pct", removed_count=removed_count
        )
```

#### Medical Safety Approval Workflow

**RU: Рабочий процесс утверждения медицинской безопасности**
**EN: Medical Safety Approval Workflow**

##### Approval Format and Artifacts

1. **Proposal Document**: `config/safety_limits.proposal.yaml`
   - Contains proposed safety limits, guardrails, and validation rules
   - Must include rationale, data sources, and risk assessment

2. **Approval Artifact**: `config/safety_limits.approval.yaml`
   - Required format:

     ```yaml
     approval_version: "1.0"
     proposal_file: "config/safety_limits.proposal.yaml"
     approved_date: "2025-01-11T00:00:00Z"
     approvers:
       - name: "Medical Advisory Board Member Name"
         role: "Medical Advisory Board"
         signature: "SHA256:abc123..."  # Cryptographic signature
       - name: "Nutrition Safety Officer Name"
         role: "Nutrition Safety Officer"
         signature: "SHA256:def456..."
       - name: "Legal Compliance Owner Name"
         role: "Legal Compliance Owner"
         signature: "SHA256:ghi789..."
     medicalSafetyApproved: true
     deployment_gate_passed: true
     ```

   - Must be committed to repository before deployment
   - Linked to PR via metadata (PR labels, commit message)

3. **PR Labels**:
   - `medical-safety-approved`: Required for deployment
   - `legal-compliance-approved`: Required for deployment
   - `nutrition-safety-reviewed`: Required for deployment

##### Responsible Roles and Minimum Approvals

- **Medical Advisory Board**: Minimum 1 approval required
  - Reviews clinical safety, health impact, medical evidence
- **Nutrition Safety Officer**: Minimum 1 approval required
  - Reviews nutritional accuracy, dietary guidelines compliance
- **Legal Compliance Owner**: Minimum 1 approval required
  - Reviews regulatory compliance (Apple/Google, local regulations)

##### Audit Trail and Storage

- **Storage Location**: `config/safety_limits.approval.yaml` (committed to repo)
- **PR Metadata**: Approval file must be referenced in PR description
- **CI Artifacts**: Approval verification results stored in CI job artifacts
- **Verification Steps**:
  1. Check presence of `config/safety_limits.approval.yaml`
  2. Validate YAML structure and required fields
  3. Verify `medicalSafetyApproved: true`
  4. Verify minimum required approvers (1 from each role)
  5. Validate signature format (optional but recommended)

##### Deployment Gate Implementation

**CI Job Name**: `check-medical-safety-approval`

**Job Configuration** (in `.github/workflows/`):

```yaml
- name: Check Medical Safety Approval
  run: |
    if [ ! -f "config/safety_limits.approval.yaml" ]; then
      echo "❌ Medical safety approval file missing"
      exit 1
    fi
    # Verify medicalSafetyApproved flag
    python scripts/verify_safety_approval.py
```

**Failure Behavior**:
- Deployment pipeline fails if `medicalSafetyApproved` is not `true`
- Deployment pipeline fails if approval file is missing
- Deployment pipeline fails if minimum approvers not met
- Error message: "Medical safety approval required before deployment. See docs/BAYESIAN_EXPANSION_STRATEGY.md"

**Verification Script**: `scripts/verify_safety_approval.py`
- Reads `config/safety_limits.approval.yaml`
- Validates structure and required fields
- Checks `medicalSafetyApproved` flag
- Verifies minimum approver requirements
- Returns exit code 0 if approved, non-zero if not

##### Workflow Steps

1. Prepare proposal: `config/safety_limits.proposal.yaml`
2. Submit to Medical Review sync (weekly)
3. Obtain approvals from required roles
4. Create `config/safety_limits.approval.yaml` with signatures
5. Commit approval file to repository
6. Add PR labels: `medical-safety-approved`, `legal-compliance-approved`, `nutrition-safety-reviewed`
7. CI gate `check-medical-safety-approval` verifies approval
8. Upon CI pass, deployment proceeds

#### Recommended Unit Tests Before Production Enablement

- **Empty history fallback**: ожидаем использование популяционного prior и корректное сообщение.
- **All values flagged as outliers**: trimmed набор пустой → fallback не ломает расчёт, аудит фиксирует `removed_count == len(history)`.
- **Extremal values**: сценарии с очень малыми/большими входами проверяют корректную работу guardrails (мин/макс не выходят за допустимые пределы).
- **Clamp dominance reporting**: кейсы, в которых доминирует `clamp_floor` или `clamp_ceiling`, возвращают ожидаемое `dominant_rule` и человеко‑читаемую `rationale`.

Важно:

- Перед продакшен‑включением персонализированных порогов требуется медицинско‑этическая ревизия и пакет валидационных тестов (unit/e2e, shadow‑mode мониторинг, экспертное подтверждение границ).
- Для критических сценариев всегда применяются абсолютные защитные границы даже при высоком доверии к персонализации.

---

## 📊 Реалистичные Метрики Успеха

### Phase 1 (3 месяца)

- ✅ Валидация данных: 90% точность обнаружения аномалий
- ✅ Рекомендации: +15–20% CTR
- ✅ Покрытие тестами: > 90%
- ✅ Время отклика: < 50ms для валидации

### Phase 2–3 (6 месяцев)

- ✅ Обнаружение аномалий: 1–2 недели раньше
- ✅ User retention: +10–15%
- ✅ Достижение целей: +15–20%

### Phase 4–5 (12 месяцев)

- ✅ Full personalization engine
- ✅ Explainable AI для всех рекомендаций
- ✅ Meta-learning в проде

## 🚦 Phase Gate Criteria

### Phase 1 – Go/No-Go Rules (exact wording)

- Go if validation accuracy ≥85% AND CTR improvement ≥+10%;
- Extend by 1 week if metrics 80–85% OR implementation debt identified;
- Revisit if accuracy <80% OR CTR regression

### Decision Authority

- Go/No-Go decision is made jointly by: Product Lead + Engineering Lead + Data Science Lead.

### Thresholds & Actions

- Go (minimum acceptable outcome): validation accuracy ≥85% AND CTR improvement ≥+10%.
  - Action: proceed to Phase 2; document learnings; lock in baselines; create follow-up tickets for non-blocking improvements.
- Extend (near-threshold or delivery risk): metrics in 80–85% band OR implementation debt identified.
  - Action: extend Phase 1 by one week; address top debt items; run targeted experiments; re-measure at week’s end; then re-evaluate Go/No-Go.
- Revisit (below threshold or negative impact): accuracy <80% OR CTR regression.
  - Action: pause progression; perform root-cause analysis; re-scope Phase 1 or pivot experiments; schedule leadership review within 3 business days; update plan before resuming.

---

## ⚠️ Критические риски и митигация

1) Data Cold Start
Проблема: у новых пользователей нет истории.
Митигация (алгоритмические подходы):

- Population priors: использование популяционных распределений (по полу/возрасту/целям) как начального prior.
- Nearest‑Neighbor Transfer: перенос параметров/гиперпараметров от k ближайших пользователей (k‑NN по признакам профиля и раннему поведению).
- Meta‑Learning / Few‑Shot: начальная инициализация параметров моделей на популяции с быстрой дообучаемостью (например, Bayesian hierarchical shrinkage).
- Cold‑Start Recommendation Bootstrap: Thompson Sampling с сильной усадкой к безопасному baseline до накопления ≥ N событий.
Рекомендуемые гиперпараметры (первичная настройка):
- Population prior strength (α_prior): 5–50 (сегмент‑зависимо); усадка уменьшается после ≥ 14 дней активности.
- k для k‑NN transfer: 5–20; метрика близости — косинусная по эмбеддингам профиля и первых 5–10 событий.
- Exploration rate для TS в холодном старте: 0.2–0.4 (декей до 0.05 за 2–4 недели).
- Минимальный объём для персонализации: N_min=50 наблюдений (или 10 дней валидных логов), иначе продолжаем смешивать с population prior (миксуем 70/30 → 30/70 по мере накопления).
Ожидаемые пороги качества:
- Целевой порог «cold‑start accuracy» (balanced accuracy для базовых задач, например, корректность рекомендаций/валидаций): ≥ 0.70 в первые 14 дней, ≥ 0.78 к дню 30.
Acceptance Criteria:
- Метрика: balanced accuracy ≥ 0.70 на когорте новых пользователей (≤ 14 дней), ≥ 0.78 на когорте 15–30 дней.
- Доля пользователей с «полезной рекомендацией» (CTR uplift vs random) ≥ +10% в первые 14 дней.
- Документация параметров α_prior, k, exploration decay; автоматические отчёты по когорте новичков в Grafana.
- Ответственные: DS/ML (настройка гиперпараметров), Backend (интеграция priors), QA (валидация метрик на сэмплах).

2) Computational Cost
Проблема: байесовские методы могут быть дорогими по CPU/памяти/IO.
Митигация (инженерные меры):

- Кэширование:
  - Что кэшируем:
    - Постериоры валидации для последнего состояния пользователя (validation posterior snapshots).
    - Промежуточные достаточные статистики (sufficient statistics) по пользователю/сегменту.
    - Результаты рекомендаций на текущий день/контекст (idempotent на период).
  - TTL:
    - Validation posterior: 15–60 мин (инвалидировать при новом событии питания).
    - Sufficient stats: 6–24 ч (инкрементальные обновления в фоне).
    - Recommendations: 30–120 мин (или до следующего значимого события).
- Батч‑обработка:
  - Batch size для оффлайна: 1k–10k пользователей на джоб (подстраивается под p95 времени и доступные ресурсы).
  - Временные окна: ночные/непиковые; дедлайны на джоб: ≤ 45 мин/партию.
- Асинхронные очереди:
  - Очередь: Redis + TaskIQ/Celery; SLA доставки задач: 99.5% on‑time.
  - Повторы: экспоненциальный backoff, макс 5 ретраев.
- Производительность API:
  - Горячий путь (кэш попал): p95 < 50 мс; p99 < 120 мс.
  - Холодный путь (без кэша): p95 < 200 мс; пиковая деградация не чаще 0.1% запросов.
Ожидаемый throughput:
- Валидация: 100–300 RPS в пике при hit‑rate кэша ≥ 80%.
- Генерация рекомендаций: 30–100 RPS синхронно; остальное — precompute/batch.
Acceptance Criteria:
- SLO API: p95 < 50 мс при кэше, p95 < 200 мс без кэша (7‑дневная медиана), error rate < 0.5%.
- Очереди: 99.5% задач выполнены вовремя; задержка p95 < 2 мин; успешность повторов ≥ 99%.
- Batch: завершение ежедневных оффлайн‑обновлений ≤ 60 мин; алерты при SLA‑нарушениях.
- Кэш: hit‑rate ≥ 80% для валидации/рекомендаций; корректная инвалидация при новых событиях.
- Ответственные: Backend/SRE (кэш/очереди/SLO), DS/ML (идемпотентность статистик), QA (нагрузочные тесты).

3) Data Privacy
Проблема: GDPR/этика требуют законности, минимизации, прозрачности и безопасности обработки.
Митигация (соответствие и аудит):

- GDPR ссылки/практики:
  - Ст. 5 (принципы обработки: минимизация, ограничение хранения).
  - Ст. 6 (правовые основания), при необходимости Ст. 9 (особые категории).
  - Ст. 13/14 (уведомления), Ст. 15–22 (DSR запросы), Ст. 25 (Privacy by Design/Default).
  - Ст. 30 (реестр операций), Ст. 32 (безопасность), Ст. 35 (DPIA при рисках).
- Логирование/аудит (только служебные данные, без лишних персональных полей):
  - request_id, user_pseudonymous_id, purpose, data_categories, model_version, features_used (категории), decision_summary, confidence, timestamp, operator/service_id.
  - DSR trace: источники данных, дата последнего обновления, политика ретенции.
- Уровни анонимизации:
  - Прод‑аналитика: псевдонимизация + агрегация; отсутствие прямых идентификаторов.
  - Research/offline: k‑анонимность k≥10, шум для чувствительных метрик; re‑identification risk ≤ 0.09.
  - Ретенция: персональные логи — 30–90 дней; аггрегаты — 12 месяцев; затем удаление/анонимизация.
- Explainability: список используемых факторов доступен пользователю (читабельный), возможность opt‑out для некоторых типов персонализации.
Acceptance Criteria:
- Политики: DPIA проведена (если применимо), реестр по Ст. 30 актуален, Privacy Notice обновлён.
- Логи: все API решений содержат обязательные поля аудита; проверка выборки (n=2000) — соответствие ≥ 99%.
- Анонимизация: k‑анонимность ≥ 10, риск ре‑идентификации ≤ 0.09 (оценка независимым скриптом); ретенция соблюдена.
- Права субъектов: время ответа на DSR ≤ 20 дней; успешность выборочной реконструкции trace ≥ 99%.
- Ответственные: Security/Legal (политики/аудит), Backend (логирование), DS/ML (анонимизация), QA (верификация выборок).

4) Model Drift
Проблема: паттерны пользователей меняются; качество моделей деградирует.
Митигация (мониторинг и перекалибровка):

- Метрики мониторинга:
  - Онлайновые: CTR/Uplift рекомендаций, калибровка вероятностей (ECE), прогнозная ошибка (sMAPE/MAE), доля аномалий.
  - Оффлайновые валидации: AUROC/PR‑AUC по свежим батчам, Brier score, PSI (Population Stability Index).
- Триггеры алертов:
  - ECE > 0.08 (3 часа подряд) или падение AUROC ≥ 5 п.п. от базовой; PSI ≥ 0.2 по ключевым признакам.
  - CTR снижение ≥ 10% к 7‑дневной базе; рост ошибок валидации > 2 п.п.
- Каденс обновлений:
  - Плановая перекалибровка priors еженедельно; полная переоценка гиперпараметров ежемесячно или при срабатывании триггера.
  - Shadow‑deploy на 10% трафика; промоут при стабильности ≥ 48 ч без деградации.
- Процесс:
  - Авто‑создание задачи (Jira) при алерте; владелец — DS/ML On‑Call.
  - Rollback‑план при деградации > 10% ключевых метрик.
Acceptance Criteria:
- Время детекции дрейфа: ≤ 1 час от события; время реакции (TTR) DS/ML: ≤ 4 часа в рабочее время.
- Перекалибровка priors выполнена ≥ 1 раз/неделю; крупные обновления — ≤ 30 дней.
- Тесты калибровки: ECE ≤ 0.05 после обновления; восстановление AUROC в пределах −2 п.п. от базовой.
- Процессность: 100% алертов создают тикет; отчёт пост‑фактум в Confluence в течение 24 часов после инцидента.
- Ответственные: DS/ML (мониторинг/перекалибровка), SRE (алерты/наблюдаемость), Product (акцепт метрик).

---

## 🎯 Финальный вердикт и ближайшие шаги

Что делать сейчас (Priority 1):

- ✅ Запуск PHASE 0 (инфраструктура): зависимости, модуль `core/bayesian/`, модели данных, миграции
- ✅ PHASE 1 Quick Wins: NutritionDataValidator + Thompson Sampling рекомендации
- ✅ Измерения результатов: A/B тесты, метрики (Prometheus/Grafana)

Что отложить (Phase 3+):

- ❌ Сложные hierarchical models (нужно больше данных)
- ❌ API-оптимизация (до выявления реальных узких мест)
- ❌ UI-персонализация (низкий ROI на раннем этапе)

Уникальная ценность PulsePlate:

- 🎯 Персонализация с учётом неопределённости
- 🧠 Explainable AI для здоровья
- 🛡️ Адаптивные safety limits
- 🚀 Самообучающиеся рекомендации

---

## 🗓️ План действий на ближайшую неделю

Неделя 1–2: PHASE 0 — Инфраструктура

- Обновить `requirements.txt` (numpy, scipy)
- Создать базовую структуру `core/bayesian/`
- Добавить модели данных (`MealEntry`, `RecommendationFeedback`)
- Подготовить миграции Alembic
- Написать базовые тесты

Неделя 3–4: PHASE 1 — Валидация

- Реализовать `NutritionDataValidator`
- Endpoint `/api/validate_meal`
- Интеграция с USDA prior
- UI-компонент для warnings (с confidence и объяснениями)
- Тесты (включая Hypothesis)

Неделя 5–6: PHASE 1 — Рекомендации

- Thompson Sampling в `recommendations.py`
- Endpoints для feedback (запись выбора)
- Dashboard для мониторинга стратегий
- A/B тестирование
- Документация

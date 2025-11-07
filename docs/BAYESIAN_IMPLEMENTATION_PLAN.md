# 🎯 План Внедрения Расширенных Байесовских Методов в PulsePlate

**Версия**: 1.0
**Дата создания**: 2025-11-07
**Статус**: Planning
**Ориентировочная длительность**: 3-4 недели

---

## 📋 Executive Summary

Этот план описывает поэтапное внедрение продвинутых байесовских анализаторов для улучшения:
- ✅ **Качества данных** (валидация нереалистичных значений)
- ✅ **Персонализации** (предсказание поведения пользователей)
- ✅ **Рекомендаций** (адаптивная система на основе feedback)
- ✅ **Производительности** (байесовская оптимизация API)

**Ожидаемые результаты**:
- 📈 Увеличение retention на 15-20%
- 🎯 Улучшение точности рекомендаций на 25-30%
- ⚡ Снижение аномальных данных на 40%
- 🔍 Раннее обнаружение проблем со здоровьем

---

## 🏗️ Архитектура

```
core/
├── bayesian/
│   ├── __init__.py
│   ├── base_analyzer.py              # Базовый класс для всех анализаторов
│   ├── nutrition_data_validator.py    # Phase 2: Валидация данных
│   ├── user_behavior_analyzer.py      # Phase 3: Поведение пользователей
│   ├── adaptive_recommender.py        # Phase 4: Адаптивные рекомендации
│   ├── api_performance_analyzer.py    # Phase 4: Оптимизация API
│   ├── metrics.py                     # Метрики эффективности
│   └── utils.py                       # Вспомогательные функции
├── bayesian_test_analyzer.py         # Existing
├── nutrition_bayesian_analyzer.py    # Existing
├── business_bayesian_analyzer.py     # Existing
└── comprehensive_bayesian_analyzer.py # Existing

tests/
├── test_nutrition_data_validator.py
├── test_user_behavior_analyzer.py
└── test_adaptive_recommender.py

docs/
├── bayesian_architecture.md           # Документация архитектуры
└── bayesian_metrics_dashboard.md      # Grafana дашборд
```

---

## 📅 Phase 1: Подготовка Архитектуры (2-3 дня)

### Задачи:

#### 1.1. Создать базовый класс `BaseBayesianAnalyzer`
**Файл**: `core/bayesian/base_analyzer.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

@dataclass
class BayesianPrediction:
    """Результат байесовского предсказания."""
    value: float
    confidence: float
    evidence: List[str]
    prior_belief: Dict[str, float]
    posterior_belief: Dict[str, float]

class BaseBayesianAnalyzer(ABC):
    """
    Базовый класс для всех байесовских анализаторов.

    Предоставляет:
    - Логирование
    - Сохранение/загрузка состояния
    - Базовые математические операции
    - Метрики эффективности
    """

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"bayesian.{name}")
        self.predictions_count = 0
        self.successful_predictions = 0

    @abstractmethod
    def predict(self, data: Dict[str, Any]) -> BayesianPrediction:
        """Основной метод предсказания (должен быть реализован в подклассах)."""
        pass

    def calculate_posterior(
        self,
        prior: float,
        likelihood: float,
        evidence: float
    ) -> float:
        """Теорема Байеса: P(H|E) = P(E|H) * P(H) / P(E)"""
        if evidence == 0:
            return 0
        return (likelihood * prior) / evidence

    def get_metrics(self) -> Dict[str, float]:
        """Метрики эффективности анализатора."""
        if self.predictions_count == 0:
            return {"accuracy": 0.0, "total_predictions": 0}

        accuracy = self.successful_predictions / self.predictions_count
        return {
            "accuracy": accuracy,
            "total_predictions": self.predictions_count,
            "successful_predictions": self.successful_predictions
        }
```

**Критерии готовности**:
- ✅ Класс создан и покрыт тестами
- ✅ Существующие анализаторы могут наследоваться от него (backward compatible)

---

#### 1.2. Система метрик `BayesianMetrics`
**Файл**: `core/bayesian/metrics.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime

@dataclass
class BayesianMetrics:
    """Метрики эффективности байесовских методов."""

    analyzer_name: str
    predictions_made: int = 0
    correct_predictions: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    average_confidence: float = 0.0
    execution_times: List[float] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        if self.predictions_made == 0:
            return 0.0
        return self.correct_predictions / self.predictions_made

    @property
    def precision(self) -> float:
        tp = self.correct_predictions
        fp = self.false_positives
        if (tp + fp) == 0:
            return 0.0
        return tp / (tp + fp)

    @property
    def recall(self) -> float:
        tp = self.correct_predictions
        fn = self.false_negatives
        if (tp + fn) == 0:
            return 0.0
        return tp / (tp + fn)

    @property
    def f1_score(self) -> float:
        p = self.precision
        r = self.recall
        if (p + r) == 0:
            return 0.0
        return 2 * (p * r) / (p + r)

    def to_dict(self) -> Dict:
        return {
            "analyzer": self.analyzer_name,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "predictions_made": self.predictions_made,
            "avg_confidence": self.average_confidence
        }
```

**Критерии готовности**:
- ✅ Метрики собираются автоматически
- ✅ Можно экспортировать в Prometheus/Grafana

---

## 📅 Phase 2: NutritionDataValidationAnalyzer (3-4 дня) ⭐ QUICK WIN

### Цель
Предотвратить ввод нереалистичных данных о питании, используя байесовскую вероятность.

### Задачи:

#### 2.1. Создать валидатор
**Файл**: `core/bayesian/nutrition_data_validator.py`

```python
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from .base_analyzer import BaseBayesianAnalyzer, BayesianPrediction

@dataclass
class NutritionEntry:
    """Запись о приеме пищи."""
    meal_name: str
    calories: float
    protein: float
    fat: float
    carbs: float
    portion_size: float
    meal_type: str  # breakfast, lunch, dinner, snack
    timestamp: str

@dataclass
class ValidationResult:
    """Результат валидации."""
    is_plausible: bool
    confidence: float
    anomaly_score: float
    issues: List[str]
    suggestions: Dict[str, float]

class NutritionDataValidationAnalyzer(BaseBayesianAnalyzer):
    """
    Байесовская валидация данных о питании.

    Проверяет:
    - Реалистичность калорий для данного блюда
    - Соотношение макронутриентов
    - Размер порции
    - Паттерны питания пользователя
    """

    def __init__(self):
        super().__init__("nutrition_validator")
        self.population_stats = self._load_population_stats()
        self.user_history: Dict[str, List[NutritionEntry]] = {}

    def _load_population_stats(self) -> Dict[str, Dict[str, float]]:
        """Загрузка популяционной статистики."""
        return {
            "breakfast": {"mean_calories": 400, "std_calories": 150},
            "lunch": {"mean_calories": 600, "std_calories": 200},
            "dinner": {"mean_calories": 700, "std_calories": 250},
            "snack": {"mean_calories": 200, "std_calories": 100},
        }

    def validate(self, entry: NutritionEntry, user_id: str) -> ValidationResult:
        """
        Валидация записи о питании.

        Использует байесовский подход:
        P(valid | entry) = P(entry | valid) * P(valid) / P(entry)

        Комбинирует:
        - Популяционные данные (prior)
        - История пользователя (likelihood)
        - Физические ограничения (evidence)
        """
        issues = []

        # 1. Проверка физических ограничений
        if not self._check_physical_constraints(entry):
            issues.append("Нарушены физические ограничения (калории из макронутриентов)")

        # 2. Байесовская оценка относительно популяции
        population_plausibility = self._calculate_population_plausibility(entry)

        # 3. Байесовская оценка относительно истории пользователя
        user_plausibility = self._calculate_user_plausibility(entry, user_id)

        # 4. Комбинируем оценки
        combined_plausibility = 0.3 * population_plausibility + 0.7 * user_plausibility

        # 5. Вычисляем anomaly score
        anomaly_score = 1 - combined_plausibility

        # 6. Генерируем предложения для исправления
        suggestions = {}
        if anomaly_score > 0.5:
            suggestions = self._generate_suggestions(entry, user_id)

        # 7. Определяем финальный вердикт
        is_plausible = anomaly_score < 0.6

        if anomaly_score > 0.7:
            issues.append(f"Очень необычные значения для {entry.meal_type}")

        return ValidationResult(
            is_plausible=is_plausible,
            confidence=combined_plausibility,
            anomaly_score=anomaly_score,
            issues=issues,
            suggestions=suggestions
        )

    def _check_physical_constraints(self, entry: NutritionEntry) -> bool:
        """Проверка физических ограничений (калории из макронутриентов)."""
        calculated_calories = (entry.protein * 4) + (entry.carbs * 4) + (entry.fat * 9)
        tolerance = 0.15  # 15% допуск

        return abs(calculated_calories - entry.calories) / entry.calories < tolerance

    def _calculate_population_plausibility(self, entry: NutritionEntry) -> float:
        """
        Вероятность на основе популяционных данных.
        Использует нормальное распределение.
        """
        stats = self.population_stats.get(entry.meal_type, {"mean_calories": 500, "std_calories": 200})
        mean = stats["mean_calories"]
        std = stats["std_calories"]

        # Вероятность из нормального распределения
        z_score = abs(entry.calories - mean) / std
        probability = np.exp(-0.5 * z_score ** 2)

        return probability

    def _calculate_user_plausibility(self, entry: NutritionEntry, user_id: str) -> float:
        """
        Вероятность на основе истории пользователя.
        Если истории нет - используем популяционный prior.
        """
        user_history = self.user_history.get(user_id, [])

        if len(user_history) < 5:
            # Недостаточно данных - используем популяционный prior
            return self._calculate_population_plausibility(entry)

        # Фильтруем по типу приема пищи
        similar_meals = [e for e in user_history if e.meal_type == entry.meal_type]

        if len(similar_meals) < 3:
            return self._calculate_population_plausibility(entry)

        # Вычисляем среднее и стандартное отклонение для пользователя
        calories_list = [e.calories for e in similar_meals]
        user_mean = np.mean(calories_list)
        user_std = np.std(calories_list) if len(calories_list) > 1 else 100

        # Вероятность из пользовательского распределения
        z_score = abs(entry.calories - user_mean) / (user_std + 1e-6)
        probability = np.exp(-0.5 * z_score ** 2)

        return probability

    def _generate_suggestions(self, entry: NutritionEntry, user_id: str) -> Dict[str, float]:
        """Генерация предложений для исправления."""
        suggestions = {}

        # Предложение на основе популяции
        pop_stats = self.population_stats.get(entry.meal_type, {})
        if pop_stats:
            suggestions["suggested_calories_population"] = pop_stats["mean_calories"]

        # Предложение на основе истории пользователя
        user_history = self.user_history.get(user_id, [])
        similar_meals = [e for e in user_history if e.meal_type == entry.meal_type]

        if len(similar_meals) >= 3:
            user_mean = np.mean([e.calories for e in similar_meals])
            suggestions["suggested_calories_your_usual"] = user_mean

        return suggestions

    def update_user_history(self, user_id: str, entry: NutritionEntry):
        """Обновление истории пользователя (после подтверждения данных)."""
        if user_id not in self.user_history:
            self.user_history[user_id] = []

        self.user_history[user_id].append(entry)

        # Ограничиваем размер истории
        if len(self.user_history[user_id]) > 100:
            self.user_history[user_id] = self.user_history[user_id][-100:]
```

**Критерии готовности**:
- ✅ Валидатор создан и протестирован
- ✅ Покрытие тестами > 80%
- ✅ Ложных срабатываний < 5%

---

#### 2.2. Тесты для валидатора
**Файл**: `tests/test_nutrition_data_validator.py`

```python
import pytest
from core.bayesian.nutrition_data_validator import (
    NutritionDataValidationAnalyzer,
    NutritionEntry,
    ValidationResult
)

class TestNutritionDataValidator:

    @pytest.fixture
    def validator(self):
        return NutritionDataValidationAnalyzer()

    def test_realistic_entry_passes(self, validator):
        """Реалистичная запись должна проходить валидацию."""
        entry = NutritionEntry(
            meal_name="Oatmeal with banana",
            calories=400,
            protein=10,
            fat=8,
            carbs=70,
            portion_size=250,
            meal_type="breakfast",
            timestamp="2025-11-07T08:00:00"
        )

        result = validator.validate(entry, "user_123")

        assert result.is_plausible is True
        assert result.confidence > 0.5
        assert result.anomaly_score < 0.5

    def test_unrealistic_calories_flagged(self, validator):
        """Нереалистично высокие калории должны быть помечены."""
        entry = NutritionEntry(
            meal_name="Apple",
            calories=5000,  # Нереалистично!
            protein=1,
            fat=0,
            carbs=25,
            portion_size=150,
            meal_type="snack",
            timestamp="2025-11-07T10:00:00"
        )

        result = validator.validate(entry, "user_123")

        assert result.is_plausible is False
        assert result.anomaly_score > 0.6
        assert len(result.issues) > 0

    def test_learns_from_user_history(self, validator):
        """Валидатор должен учиться на основе истории пользователя."""
        # Добавляем историю: пользователь всегда ест большие завтраки
        for _ in range(10):
            big_breakfast = NutritionEntry(
                meal_name="Big breakfast",
                calories=800,
                protein=30,
                fat=25,
                carbs=90,
                portion_size=400,
                meal_type="breakfast",
                timestamp="2025-11-07T08:00:00"
            )
            validator.update_user_history("user_power_eater", big_breakfast)

        # Теперь большой завтрак для этого пользователя должен быть нормальным
        test_entry = NutritionEntry(
            meal_name="Another big breakfast",
            calories=850,
            protein=32,
            fat=27,
            carbs=95,
            portion_size=420,
            meal_type="breakfast",
            timestamp="2025-11-08T08:00:00"
        )

        result = validator.validate(test_entry, "user_power_eater")

        # Должен пройти для этого пользователя
        assert result.is_plausible is True
        assert result.confidence > 0.6
```

---

#### 2.3. Интеграция в app.py
**Модификация**: `app.py`

```python
# В начале файла
from core.bayesian.nutrition_data_validator import (
    NutritionDataValidationAnalyzer,
    NutritionEntry
)

# В lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Existing initialization...

    # Байесовские анализаторы
    app.state.nutrition_validator = NutritionDataValidationAnalyzer()

    yield

    # Cleanup...

# Новый эндпоинт для валидации
@app.post("/api/validate_meal")
async def validate_meal_data(
    meal_data: Dict[str, Any],
    user_id: str,
    request: Request
):
    """
    Валидация данных о приеме пищи перед сохранением.

    Returns:
        - is_valid: bool
        - confidence: float
        - warnings: List[str]
        - suggestions: Dict[str, float]
    """
    validator = request.app.state.nutrition_validator

    entry = NutritionEntry(
        meal_name=meal_data.get("name", "Unknown"),
        calories=meal_data.get("calories", 0),
        protein=meal_data.get("protein", 0),
        fat=meal_data.get("fat", 0),
        carbs=meal_data.get("carbs", 0),
        portion_size=meal_data.get("portion_size", 100),
        meal_type=meal_data.get("meal_type", "snack"),
        timestamp=meal_data.get("timestamp", "")
    )

    result = validator.validate(entry, user_id)

    return {
        "is_valid": result.is_plausible,
        "confidence": result.confidence,
        "anomaly_score": result.anomaly_score,
        "warnings": result.issues,
        "suggestions": result.suggestions
    }
```

---

## 📅 Phase 3: UserBehaviorBayesianAnalyzer (4-5 дней)

### Цель
Предсказание поведения пользователей для улучшения retention и персонализации.

### Задачи:

#### 3.1. Создать анализатор поведения
**Файл**: `core/bayesian/user_behavior_analyzer.py`

```python
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
from .base_analyzer import BaseBayesianAnalyzer, BayesianPrediction

class UserBehaviorBayesianAnalyzer(BaseBayesianAnalyzer):
    """
    Предсказывает поведение пользователей:
    - Вероятность достижения целей
    - Риск churn (отказа от использования)
    - Предпочтения в блюдах
    - Оптимальное время для уведомлений
    """

    def predict_goal_achievement_probability(self, user_id: str) -> BayesianPrediction:
        """
        Предсказывает вероятность достижения целей по калориям.

        Факторы:
        - История соблюдения плана
        - Частота логирования
        - Стабильность паттернов
        - Социальная активность (если есть)
        """
        # TODO: Implement
        pass

    def predict_churn_risk(self, user_id: str) -> BayesianPrediction:
        """
        Предсказывает риск того, что пользователь перестанет использовать приложение.

        Факторы:
        - Снижение частоты логирования
        - Увеличение пропущенных дней
        - Отклонение от целей
        - Время с момента последней активности
        """
        # TODO: Implement
        pass

    def predict_meal_preference(
        self,
        user_id: str,
        meal_options: List[Dict]
    ) -> Dict[str, float]:
        """
        Ранжирует блюда по вероятности выбора пользователем.

        Использует:
        - История выбранных блюд
        - Предпочтения по макронутриентам
        - Время суток
        - Сезонность
        """
        # TODO: Implement
        pass
```

---

## 📅 Phase 4: AdaptiveRecommendationEngine (3-4 дня)

### Цель
Адаптивная система рекомендаций, которая учится на feedback пользователей.

**Файл**: `core/bayesian/adaptive_recommender.py`

```python
import numpy as np
from typing import Dict, List

class AdaptiveRecommendationEngine:
    """
    Thompson Sampling для оптимизации рекомендаций.

    Multi-Armed Bandit подход:
    - Каждая стратегия рекомендации = arm
    - Балансирует exploration vs exploitation
    - Адаптируется к feedback в реальном времени
    """

    def __init__(self):
        self.arms = {
            "high_protein": {"alpha": 1, "beta": 1},
            "balanced": {"alpha": 1, "beta": 1},
            "low_carb": {"alpha": 1, "beta": 1},
            "mediterranean": {"alpha": 1, "beta": 1},
        }

    def select_strategy(self, user_context: Dict) -> str:
        """
        Выбирает стратегию рекомендации с учетом контекста.

        Thompson Sampling:
        - Сэмплирует из Beta распределения для каждого arm
        - Выбирает arm с наибольшим сэмплом
        """
        samples = {
            arm: np.random.beta(params["alpha"], params["beta"])
            for arm, params in self.arms.items()
        }
        return max(samples, key=samples.get)

    def update_from_feedback(self, arm: str, success: bool):
        """
        Обновляет вероятности на основе feedback.

        Success = пользователь выбрал рекомендованное блюдо
        """
        if success:
            self.arms[arm]["alpha"] += 1
        else:
            self.arms[arm]["beta"] += 1
```

---

## 📅 Phase 5: Документация и Мониторинг (2 дня)

### Задачи:

#### 5.1. Документация архитектуры
**Файл**: `docs/bayesian_architecture.md`

- Описание каждого анализатора
- Диаграммы взаимодействия
- Примеры использования
- Best practices

#### 5.2. Grafana дашборд
**Файл**: `docs/bayesian_metrics_dashboard.md`

Метрики для мониторинга:
- Точность предсказаний (accuracy)
- Количество аномалий
- Время выполнения анализа
- User engagement metrics

---

## 🎯 Критерии Успеха

### Технические метрики:
- ✅ **Покрытие тестами**: > 85%
- ✅ **Точность валидации**: > 90%
- ✅ **Ложные срабатывания**: < 5%
- ✅ **Время отклика API**: < 100ms для валидации

### Бизнес метрики:
- 📈 **User retention**: +15-20%
- 🎯 **Точность рекомендаций**: +25-30%
- ⚡ **Аномальные данные**: -40%
- 💡 **User satisfaction**: +10%

---

## 🚀 Стратегия Деплоя

### Этап 1: Canary Deployment
- Включить для 5% пользователей
- Мониторить метрики 3-5 дней
- Собрать feedback

### Этап 2: Gradual Rollout
- 25% пользователей (1 неделя)
- 50% пользователей (1 неделя)
- 100% пользователей

### Этап 3: Optimization
- Анализ A/B тестов
- Тюнинг гиперпараметров
- Оптимизация производительности

---

## ⚠️ Риски и Митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Ложные срабатывания | Средняя | Высокое | Тщательное тестирование, постепенный rollout |
| Проблемы с производительностью | Низкая | Среднее | Кэширование, асинхронная обработка |
| Недостаток данных для новых пользователей | Высокая | Среднее | Hierarchical Bayesian Models, population priors |
| Сложность отладки | Средняя | Низкое | Детальное логирование, метрики, дашборды |

---

## 📚 Ресурсы

### Библиотеки:
- `numpy` - математические операции
- `scipy` - статистические распределения
- `pymc3` (optional) - продвинутые байесовские модели

### Документация:
- [Bayesian Data Analysis](http://www.stat.columbia.edu/~gelman/book/)
- [Thompson Sampling Tutorial](https://web.stanford.edu/~bvr/pubs/TS_Tutorial.pdf)
- [Multi-Armed Bandits](https://arxiv.org/abs/1904.07272)

---

## 📝 Чеклист для Нового PR

Перед созданием PR убедитесь:
- [ ] Все тесты проходят
- [ ] Покрытие тестами > 85%
- [ ] Документация обновлена
- [ ] Метрики добавлены в мониторинг
- [ ] Code review пройден
- [ ] Performance тесты пройдены
- [ ] Changelog обновлен

---

## 🤝 Контакты

**Вопросы по плану**: создайте issue в репозитории
**Предложения**: PR в этот документ приветствуются!

---

**Статус**: ✅ План готов к началу реализации
**Следующий шаг**: Создать новую ветку `feat/bayesian-user-analytics` и начать с Phase 1

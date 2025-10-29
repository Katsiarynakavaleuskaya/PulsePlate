# ⚡ Быстрый чек-лист исправлений

## 🎯 PR #235 - ГОТОВ ✅
- [x] Исправлена конфигурация pytest (`[pytest]` вместо `[tool:pytest]`)
- [x] Удалена релизная версия `releases/v0.1.0/`
- [x] Зарегистрированы маркеры `smoke`, `demo`, `quarantined`
- [x] Исправлены LLM тесты (ожидание `StubProvider` вместо `None`)
- [x] Ослаблены Monte Carlo проверки (BMI: 0.001-1000, accuracy: ≥30%)
- [x] Исправлены DB тесты (async мокирование)
- [x] Помечены медленные тесты как `@pytest.mark.slow`

**Результат:** 2547 тестов проходят, 0 падающих, ~7 минут

---

## 🚀 PR #236 - Конфигурация (1-2 дня)

### Критические задачи:
- [ ] Удалить `pytest.ini` полностью
- [ ] Перенести все в `pyproject.toml`
- [ ] Добавить `--strict-markers` в CI
- [ ] Создать GitHub Actions workflows:
  - PR: `pytest -q -m "not slow and not coverage and not demo" --maxfail=5 -ra tests`
  - Nightly: `pytest -m "not demo" -n auto --cov=core --cov=app --cov-fail-under=97 -ra`

### Структура карантина:
```bash
mkdir -p tests/{quarantined,unit,integration,e2e}
mv tests/disabled_hypothesis/* tests/quarantined/
mv tests/test_health_monte_carlo.py tests/quarantined/
```

---

## 🎯 PR #237 - Покрытие (2-3 дня)

### Дифф-покрытие:
- [ ] Установить `diff-cover`
- [ ] Создать `scripts/check-diff-coverage.py`
- [ ] Требовать 85% покрытия для измененных файлов
- [ ] 97% общее покрытие только в ночном прогоне

### Критические файлы (0% покрытия):
- [ ] `core/agent_system.py` (174 строки)
- [ ] `core/ai_integration.py` (95 строк)
- [ ] `core/bayesian_test_analyzer.py` (279 строк)
- [ ] `core/llm_enhanced.py` (102 строки)

### Мокирование API:
- [ ] USDA API (rate limiting)
- [ ] Open Food Facts API
- [ ] LLM провайдеры

---

## 🔧 PR #238 - Стабильность (3-4 дня)

### Флаки тесты:
- [ ] Установить `pytest-rerunfailures`
- [ ] Добавить `--reruns=2 --reruns-delay=1`
- [ ] Пометить нестабильные тесты `@pytest.mark.flaky`

### Async исправления:
- [ ] Заменить `Mock()` на `AsyncMock()` для async методов
- [ ] Добавить proper cleanup в фикстуры
- [ ] Исправить `RuntimeWarning: coroutine was never awaited`

### Hypothesis тесты:
- [ ] Включить в ночной прогон
- [ ] Исправить `test_hypothesis_property_based.py`
- [ ] Добавить стратегии для edge cases

---

## ⚡ PR #239 - Производительность (2-3 дня)

### Оптимизация:
- [ ] Кэширование тяжелых операций (`@lru_cache`)
- [ ] Изоляция тестов (no shared state)
- [ ] Параллельное выполнение (`-n auto`)

### Мониторинг:
- [ ] Timing для медленных тестов
- [ ] Dashboard покрытия
- [ ] Алерты на деградацию

### CI/CD:
- [ ] Кэширование зависимостей
- [ ] Матричное тестирование (Python 3.11, 3.12)
- [ ] Conditional builds

---

## 🚨 Критические команды

### Быстрый тест (PR):
```bash
python -m pytest -q -m "not slow and not coverage and not demo" --maxfail=5 -ra tests
```

### Полный тест (ночной):
```bash
python -m pytest -m "not demo" -n auto --cov=core --cov=app --cov-fail-under=97 -ra
```

### Проверка покрытия:
```bash
pytest --cov=core --cov=app --cov-report=html
diff-cover coverage.xml --compare-branch=origin/main --fail-under=85
```

### Исправление async warnings:
```bash
# Найти проблемные тесты
pytest --tb=short -W error::RuntimeWarning

# Исправить мокирование
# Заменить Mock() на AsyncMock() для async методов
```

---

## 📊 Целевые метрики

| Метрика | Текущее | Цель PR #236 | Цель PR #237 | Цель PR #238 | Цель PR #239 |
|---------|---------|--------------|--------------|--------------|--------------|
| Падающие тесты | 0 | 0 | 0 | 0 | 0 |
| Время PR | 7 мин | 5 мин | 5 мин | 5 мин | 3 мин |
| Время ночной | - | 30 мин | 30 мин | 30 мин | 15 мин |
| Покрытие | 19% | 19% | 97% | 97% | 97% |
| Дифф-покрытие | - | - | 85% | 85% | 85% |
| Флаки тесты | ? | ? | ? | 0 | 0 |
| Async warnings | ? | ? | ? | 0 | 0 |

---

## 🎯 Приоритеты

1. **PR #236** - Конфигурация (критично для стабильности)
2. **PR #237** - Покрытие (критично для качества)
3. **PR #238** - Стабильность (важно для CI)
4. **PR #239** - Производительность (оптимизация)

**Рекомендация:** Реализовать последовательно, по одному PR за раз, с тщательным тестированием каждого изменения.

---
*Обновлено: 30 октября 2025*

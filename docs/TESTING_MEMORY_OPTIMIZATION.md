# 🧠 Оптимизация памяти для больших тестовых наборов (5000+ тестов)

## Проблема
При ~5000+ тестах возникают проблемы:
- **MemoryError** на CI runners (GitHub Actions, GitLab CI)
- Медленная коллекция тестов (pytest собирает все элементы в память)
- Накопление мусора между тестами
- Утечки памяти в фикстурах с длительным жизненным циклом

## ✅ Реализованные решения

### 1. Tenant-Based Шардирование
**Файл:** `pytest_sharding.py`

Разделение тестов по функциональным доменам:
- **Shard 1 (app_api)**: 746 тестов - API и приложение
- **Shard 2 (database)**: 560 тестов - База данных
- **Shard 3 (vip_premium)**: VIP и premium функции
- **Shard 4 (analytics)**: 216 тестов - Bayesian аналитика
- **Shard 5 (core)**: Ядро бизнес-логики
- **Shard 6 (planning_export)**: Планирование и экспорт

**Использование:**
```bash
# Запуск конкретного шарда
pytest --shard-id=1 tests/

# Последовательный запуск всех шардов (CI)
for i in {1..6}; do
    pytest --shard-id=$i tests/ --cov --cov-append
done

# Параллельный запуск (ограниченный - 2-3 воркера макс)
./run_sharded_tests.sh --parallel-2 --cov
```

**Преимущества:**
- ✅ Каждый шард загружает в память только свои тесты
- ✅ Логическая группировка - легче отлаживать
- ✅ Можно запускать критичные шарды отдельно

### 2. Маркировка тяжёлых тестов

**Маркеры в pytest.ini:**
```python
@pytest.mark.heavy       # Тяжёлые тесты (интеграция, LLM, большие датасеты)
@pytest.mark.integration # Требуют внешние сервисы
@pytest.mark.slow        # Медленные тесты (>1s)
@pytest.mark.serial      # Запуск последовательно (не параллельно)
```

**Исключение тяжёлых тестов из PR:**
```bash
# Быстрая проверка PR (без heavy)
pytest -m "not heavy" tests/

# Полный прогон (nightly/release)
pytest tests/
```

**Когда маркировать тест как heavy:**
- Интеграция с внешними API (OpenAI, Stripe, database replicas)
- Большие датасеты (>1000 строк, >10MB файлы)
- LLM-провайдеры (GPT, Claude, embedding модели)
- Тесты с длительной инициализацией (>2s setup)
- Тесты, создающие много объектов в памяти

**Пример маркировки:**
```python
@pytest.mark.heavy
@pytest.mark.integration
def test_openai_embeddings_batch():
    """Process 1000 recipes through OpenAI embeddings."""
    # Тяжёлый тест - маркируем
    pass

@pytest.mark.heavy
def test_large_nutrition_dataset():
    """Load and process USDA nutrition database (50k items)."""
    # Большой датасет - маркируем
    pass
```

### 3. File-Based Sharding (альтернатива pytest-split)

**Проблема pytest-split:**
- Собирает ВСЕ тесты в память перед шардированием
- `dict.fromkeys(items)` вызывает MemoryError при 5000+ тестах

**Решение - хеширование имён файлов:**
```bash
# Функция для выбора файлов по MD5-хешу
select_files_for_shard() {
  python - "$1" "$2" <<'PY'
import glob, hashlib, sys, shlex
group = int(sys.argv[1])
groups = int(sys.argv[2])
files = sorted(glob.glob('tests/**/*.py', recursive=True))
test_files = [f for f in files if f.endswith('_test.py') or f.startswith('tests/test_')]
selected = []
for f in test_files:
    h = int(hashlib.md5(f.encode('utf-8')).hexdigest(), 16)
    if (h % groups) + 1 == group:
        selected.append(f)
print(' '.join(shlex.quote(x) for x in selected))
PY
}

# Использование в CI
FILES=$(select_files_for_shard "$GROUP" "$GROUPS")
python -m pytest $FILES --cov=. --cov-append
```

**Преимущества:**
- ✅ Нет глобальной коллекции тестов
- ✅ Постоянное распределение (один файл всегда в одном шарде)
- ✅ Минимальное потребление памяти

## 🔧 Рекомендуемые практики

### Изоляция ресурсов
```python
@pytest.fixture(scope="function")  # НЕ session!
def database_client():
    """Создаём и уничтожаем клиент для каждого теста."""
    client = DatabaseClient()
    yield client
    client.close()  # Явное освобождение
    del client      # Помощь GC
```

### Lazy-инициализация
```python
# ❌ Плохо - импорт тяжёлой зависимости на уровне модуля
import heavy_ml_library

# ✅ Хорошо - импорт только когда нужен
def test_ml_model():
    import heavy_ml_library  # Lazy import
    model = heavy_ml_library.load_model()
    ...
```

### Очистка после тестов
```python
def teardown_module():
    """Очистка после модуля тестов."""
    # Удаляем временные файлы
    shutil.rmtree("temp_data", ignore_errors=True)

    # Очищаем глобальные кэши
    import gc
    gc.collect()

    # Закрываем соединения
    close_all_database_connections()
```

### Mock вместо реальных сервисов
```python
# ❌ Плохо - реальный OpenAI API в каждом тесте
def test_embedding():
    result = openai.Embedding.create(...)

# ✅ Хорошо - mock для быстрых unit-тестов
@pytest.mark.unit
def test_embedding_processing(monkeypatch):
    monkeypatch.setattr("openai.Embedding.create",
                       Mock(return_value={"data": [...]}))
    # Быстро, без сети, без API rate limits
```

## 📊 Мониторинг

### Отслеживание тяжёлых тестов
```bash
# Топ-10 самых медленных тестов
pytest --durations=10

# Профилирование памяти
pytest --memray tests/

# Анализ coverage по шардам
for i in {1..6}; do
    echo "Shard $i coverage:"
    pytest --shard-id=$i --cov --cov-report=term-missing | tail -5
done
```

### Metrics для CI
Добавьте в GitHub Actions:
```yaml
- name: Memory monitoring
  run: |
    free -h  # До тестов
    pytest tests/ --maxfail=1
    free -h  # После тестов

- name: Test duration report
  run: |
    pytest --durations=20 --durations-min=1.0
```

## 🚀 CI/CD конфигурация

### Быстрая проверка PR (без heavy)
```yaml
- name: Fast PR tests
  run: pytest -m "not heavy and not slow" --maxfail=5
```

### Полный прогон (nightly)
```yaml
- name: Full test suite
  run: |
    for shard in {1..6}; do
      pytest --shard-id=$shard tests/ --cov --cov-append
    done
    coverage report --fail-under=97
```

### Parallel с ограничением
```yaml
- name: Parallel shards (memory-safe)
  run: |
    # Только 2 воркера одновременно
    pytest --shard-id=1 tests/ &
    pytest --shard-id=2 tests/ &
    wait

    pytest --shard-id=3 tests/ &
    pytest --shard-id=4 tests/ &
    wait
```

## 🎯 Чеклист перед добавлением теста

- [ ] Тест помечен подходящими маркерами (`@pytest.mark.heavy`, etc.)
- [ ] Фикстуры имеют правильный scope (function > module > session)
- [ ] Ресурсы явно освобождаются (close, del, gc.collect)
- [ ] Используются mock для внешних сервисов (где возможно)
- [ ] Нет утечек памяти (проверено с `--memray`)
- [ ] Тест в правильном tenant-шарде (по функциональности)

## 📚 Дополнительные ресурсы

- [Memray — Python memory profiler](https://github.com/bloomberg/memray)
- [GitHub Actions Memory Limits](https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners)
- [pytest-split — Test sharding for pytest](https://github.com/jerry-git/pytest-split)

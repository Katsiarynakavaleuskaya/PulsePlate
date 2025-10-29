# 🎯 Планы коррекции на следующие PR

## PR #236: Конфигурация и инфраструктура
**Приоритет:** 🔴 Критический  
**Время:** 1-2 дня  
**Цель:** Стабильная конфигурация pytest и CI/CD

### 📋 Задачи

#### 1. Единый конфиг pytest
```bash
# Удалить pytest.ini
rm pytest.ini

# Обновить pyproject.toml
[tool.pytest.ini_options]
pythonpath = "."
testpaths = ["tests"]
addopts = "-q -m 'not slow and not coverage and not demo' -n auto --maxfail=5 -ra --strict-markers"
asyncio_mode = "auto"
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests", 
    "unit: marks tests as unit tests",
    "e2e: marks tests as end-to-end tests",
    "performance: marks tests as performance tests",
    "coverage: marks tests as coverage tests",
    "monte_carlo: marks tests as Monte Carlo tests",
    "bayesian: marks tests as Bayesian analysis tests",
    "hypothesis: marks tests using Hypothesis property-based testing",
    "smoke: marks tests as smoke tests",
    "demo: marks tests as demo tests",
    "quarantined: marks tests as quarantined (skip in PR)"
]
filterwarnings = [
    "ignore::DeprecationWarning",
    "ignore::PendingDeprecationWarning",
    "ignore::UserWarning:pydantic.*"
]
```

#### 2. GitHub Actions workflows
```yaml
# .github/workflows/pr-tests.yml
name: PR Tests (Fast)
on: [pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run fast tests
        run: pytest -q -m "not slow and not coverage and not demo" --maxfail=5 -ra tests

# .github/workflows/nightly-tests.yml  
name: Nightly Tests (Full)
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM daily
  workflow_dispatch:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run full tests with coverage
        run: pytest -m "not demo" -n auto --cov=core --cov=app --cov-report=xml --cov-fail-under=97 -ra
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

#### 3. Карантин проблемных тестов
```bash
# Создать структуру
mkdir -p tests/quarantined
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/e2e

# Переместить проблемные тесты
mv tests/disabled_hypothesis/* tests/quarantined/
mv tests/test_health_monte_carlo.py tests/quarantined/
```

### ✅ Критерии успеха
- [ ] 0 конфликтов конфигурации
- [ ] PR тесты <5 минут
- [ ] Ночные тесты <30 минут
- [ ] 0 unknown markers warnings

---

## PR #237: Покрытие кода и качество
**Приоритет:** 🔴 Критический  
**Время:** 2-3 дня  
**Цель:** 97% покрытие кода с дифф-политикой

### 📋 Задачи

#### 1. Дифф-покрытие для PR
```bash
# Установить diff-cover
pip install diff-cover

# Добавить в requirements.txt
diff-cover>=7.0.0

# Создать скрипт
# scripts/check-diff-coverage.py
#!/usr/bin/env python3
import subprocess
import sys

def check_diff_coverage():
    """Проверить покрытие только измененных файлов"""
    # Генерировать coverage.xml
    subprocess.run([
        "pytest", "--cov=core", "--cov=app", 
        "--cov-report=xml", "tests/"
    ], check=True)
    
    # Проверить дифф-покрытие
    result = subprocess.run([
        "diff-cover", "coverage.xml", 
        "--compare-branch=origin/main",
        "--fail-under=85"
    ])
    
    return result.returncode == 0

if __name__ == "__main__":
    sys.exit(0 if check_diff_coverage() else 1)
```

#### 2. Исправление критически низкого покрытия

**Файлы с 0% покрытия:**
- `core/agent_system.py` (174 строки)
- `core/ai_integration.py` (95 строк)  
- `core/bayesian_test_analyzer.py` (279 строк)
- `core/llm_enhanced.py` (102 строки)

**План действий:**
```python
# tests/test_agent_system_coverage.py
import pytest
from unittest.mock import Mock, patch
from core.agent_system import AgentOrchestrator, TaskResult

class TestAgentSystemCoverage:
    def test_agent_orchestrator_init(self):
        """Test AgentOrchestrator initialization"""
        orchestrator = AgentOrchestrator()
        assert orchestrator is not None
        assert hasattr(orchestrator, 'agents')
    
    def test_task_result_creation(self):
        """Test TaskResult creation"""
        result = TaskResult(
            task_id="test_task",
            success=True,
            data={"test": "data"},
            error_message=None
        )
        assert result.task_id == "test_task"
        assert result.success is True
        assert result.data == {"test": "data"}
    
    @pytest.mark.asyncio
    async def test_execute_task_success(self):
        """Test successful task execution"""
        orchestrator = AgentOrchestrator()
        
        with patch.object(orchestrator, 'agents', {}):
            result = await orchestrator.execute_task("test_task", {"input": "data"})
            assert isinstance(result, TaskResult)
```

#### 3. Мокирование внешних зависимостей
```python
# tests/conftest.py
import pytest
from unittest.mock import Mock, patch

@pytest.fixture(autouse=True)
def mock_external_apis():
    """Mock external APIs to prevent rate limiting"""
    with patch('core.food_apis.usda_client.httpx.get') as mock_usda, \
         patch('core.food_apis.openfoodfacts_client.httpx.get') as mock_off:
        
        # Mock successful responses
        mock_usda.return_value.json.return_value = {
            "foods": [{"fdcId": 1, "description": "Test food"}]
        }
        mock_off.return_value.json.return_value = {
            "products": [{"id": "1", "product_name": "Test product"}]
        }
        
        yield
```

### ✅ Критерии успеха
- [ ] 97% общее покрытие
- [ ] 85% дифф-покрытие для PR
- [ ] 0% покрытие для критических файлов >80%
- [ ] 0 rate limiting ошибок

---

## PR #238: Тестирование и стабильность  
**Приоритет:** 🟡 Средний  
**Время:** 3-4 дня  
**Цель:** Устранение флаки тестов и async warnings

### 📋 Задачи

#### 1. Исправление флаки тестов
```bash
# Установить pytest-rerunfailures
pip install pytest-rerunfailures

# Добавить в pyproject.toml
[tool.pytest.ini_options]
addopts = "-q -m 'not slow and not coverage and not demo' -n auto --maxfail=5 -ra --strict-markers --reruns=2 --reruns-delay=1"
```

**Проблемные тесты для исправления:**
```python
# tests/test_api_endpoint.py
@pytest.mark.flaky(reruns=2, reruns_delay=1)
def test_api_endpoint_with_retry():
    """Test API endpoint with automatic retry"""
    # Implementation with proper error handling

# tests/test_database_operations.py  
@pytest.mark.flaky(reruns=3, reruns_delay=2)
def test_database_connection_retry():
    """Test database connection with retry logic"""
    # Implementation with connection pooling
```

#### 2. Async/await исправления
```python
# Исправить RuntimeWarning: coroutine was never awaited

# Плохо
@pytest.fixture
def mock_async_function():
    return Mock()

# Хорошо
@pytest.fixture
def mock_async_function():
    return AsyncMock()

# Исправить cleanup
@pytest.fixture
async def async_resource():
    resource = await create_resource()
    try:
        yield resource
    finally:
        await resource.cleanup()
```

#### 3. Property-based тестирование
```python
# tests/test_hypothesis_property_based.py
import pytest
from hypothesis import given, strategies as st
from core.bmi_core import calculate_bmi

class TestBMIPropertyBased:
    @given(
        weight=st.floats(min_value=10.0, max_value=300.0),
        height=st.floats(min_value=0.5, max_value=2.5)
    )
    def test_bmi_calculation_properties(self, weight, height):
        """Test BMI calculation with property-based testing"""
        bmi = calculate_bmi(weight, height)
        
        # BMI should be positive
        assert bmi > 0
        
        # BMI should be within reasonable range
        assert 5 <= bmi <= 100
        
        # BMI should increase with weight
        bmi_higher_weight = calculate_bmi(weight * 1.1, height)
        assert bmi_higher_weight > bmi
```

### ✅ Критерии успеха
- [ ] 0 флаки тестов
- [ ] 0 RuntimeWarning: coroutine was never awaited
- [ ] Hypothesis тесты включены в ночной прогон
- [ ] 99.9% стабильность тестов

---

## PR #239: Производительность и мониторинг
**Приоритет:** 🟡 Средний  
**Время:** 2-3 дня  
**Цель:** Оптимизация производительности и мониторинг

### 📋 Задачи

#### 1. Оптимизация тестов
```python
# tests/conftest.py
import pytest
from functools import lru_cache

@pytest.fixture(scope="session")
@lru_cache(maxsize=1)
def cached_heavy_computation():
    """Cache expensive computations across tests"""
    return expensive_computation()

@pytest.fixture(autouse=True)
def isolate_tests():
    """Ensure test isolation"""
    # Setup
    yield
    # Cleanup
    cleanup_test_data()
```

#### 2. Мониторинг и метрики
```python
# scripts/test_metrics.py
import time
import json
from pathlib import Path

class TestMetrics:
    def __init__(self):
        self.metrics = {}
    
    def record_test_time(self, test_name, duration):
        self.metrics[test_name] = duration
    
    def save_metrics(self, filepath="test_metrics.json"):
        with open(filepath, 'w') as f:
            json.dump(self.metrics, f, indent=2)
    
    def get_slow_tests(self, threshold=5.0):
        return {k: v for k, v in self.metrics.items() if v > threshold}

# Использование в тестах
@pytest.fixture(autouse=True)
def track_test_time(request):
    start_time = time.time()
    yield
    duration = time.time() - start_time
    if duration > 1.0:  # Log slow tests
        print(f"Slow test: {request.node.name} took {duration:.2f}s")
```

#### 3. CI/CD оптимизация
```yaml
# .github/workflows/optimized-ci.yml
name: Optimized CI
on: [push, pull_request]

jobs:
  test-matrix:
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
        test-group: ['unit', 'integration', 'e2e']
    
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest-xdist
      
      - name: Run tests
        run: |
          pytest tests/${{ matrix.test-group }}/ \
            -n auto \
            --durations=10 \
            --junitxml=test-results-${{ matrix.test-group }}.xml
      
      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results-${{ matrix.test-group }}
          path: test-results-*.xml
```

### ✅ Критерии успеха
- [ ] PR тесты <3 минуты
- [ ] Ночные тесты <15 минут  
- [ ] 0 медленных тестов (>10s)
- [ ] 100% кэш hit rate для зависимостей

---

## 📊 Общие метрики успеха

### Текущее состояние (PR #235):
- ✅ 0 падающих тестов
- ✅ 2547 проходящих тестов
- ✅ ~7 минут время выполнения
- ✅ 100% успешность в PR

### Цели после всех PR:
- 🎯 99.9% стабильность тестов
- 🎯 <3 минуты время PR тестов
- 🎯 <15 минут время ночных тестов
- 🎯 97% общее покрытие кода
- 🎯 85% дифф-покрытие для PR
- 🎯 0 флаки тестов
- 🎯 0 async warnings

## 🚨 Критические риски и митигация

### 1. Rate limiting внешних API
**Риск:** 429 Too Many Requests в CI  
**Митигация:** Агрессивное мокирование, кэширование ответов

### 2. Memory leaks в async тестах
**Риск:** `RuntimeWarning: coroutine was never awaited`  
**Митигация:** Proper cleanup, async context managers

### 3. Конфликты конфигурации
**Риск:** `pytest.ini` vs `pyproject.toml`  
**Митигация:** Единый источник конфигурации

### 4. Флаки тесты в CI
**Риск:** Случайные падения в CI  
**Митигация:** `pytest-rerunfailures`, изоляция тестов

## 📝 Рекомендации по реализации

1. **Последовательность:** Реализовать планы по одному PR за раз
2. **Тестирование:** Тщательно тестировать каждое изменение
3. **Мониторинг:** Отслеживать метрики после каждого PR
4. **Откат:** Подготовить план отката для каждого изменения

---
*Планы созданы на основе анализа ошибок в PR #235*

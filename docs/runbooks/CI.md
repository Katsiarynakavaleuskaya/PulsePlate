# 🚀 Настройка CI/CD для PulsePlate

## 📋 Обзор

Проект настроен для автоматической проверки качества кода и покрытия тестами через:

- **GitHub Actions** - CI/CD pipeline
- **Codecov** - мониторинг покрытия тестами
- **Pre-commit hooks** - локальная проверка перед коммитом

## 🎯 Требования

### Покрытие тестами: 97%

- Минимальное покрытие: **97%**
- Текущее покрытие: **93%**
- Статус: ⚠️ **Требует улучшения**

## 🔧 Настройка

### 1. GitHub Actions

Файл: `.github/workflows/ci.yml`

```yaml
# Автоматически запускается на:
# - Push в main/develop
# - Pull Request в main/develop

# Проверки:
- ✅ Pre-commit hooks (linting, formatting)
- ✅ Тесты с покрытием 97%+
- ✅ Security scan (Bandit)
- ✅ Upload coverage в Codecov
```

### 2. Codecov

Файл: `codecov.yml`

```yaml
coverage:
  target: 97%
  threshold: 1%
  range: 97..100
```

### 3. Pre-commit Hooks

Файл: `.pre-commit-config.yaml`

```yaml
# Автоматические проверки:
- ✅ Trailing whitespace
- ✅ End of file fixer
- ✅ YAML validation
- ✅ Black formatting
- ✅ Ruff linting
- ✅ MyPy type checking
- ✅ Pytest с покрытием 97%
```

## 🛠 Локальная разработка

### Установка pre-commit

```bash
pip install pre-commit
pre-commit install
```

### Проверка покрытия

```bash
# Быстрая проверка
./scripts/check_coverage_97.sh

# Детальный анализ
./scripts/analyze_coverage_gaps.py

# Ручная проверка
python -m pytest --cov=. --cov-fail-under=97 -q
```

## 📊 Мониторинг покрытия

### Критические файлы (требуют улучшения)

1. **app.py** - 86% → 97% (116 непокрытых строк)
2. **app/routers/vip.py** - 69% → 97% (101 непокрытая строка)
3. **conftest.py** - 75% → 97% (6 непокрытых строк)

### HTML отчеты

После запуска тестов:

```bash
open htmlcov/index.html
```

## 🚨 Блокирующие условия

Git push будет **заблокирован** если:

- ❌ Покрытие тестами < 97%
- ❌ Pre-commit hooks падают
- ❌ MyPy находит ошибки типизации
- ❌ Ruff находит критичные ошибки

## ✅ Успешный CI/CD

Для успешного прохождения всех проверок:

1. **Локально**: `pre-commit run --all-files`
2. **Тесты**: `./scripts/check_coverage_97.sh`
3. **Коммит**: `git commit -m "feat: add feature"`
4. **Push**: `git push origin main`

## 🔗 Полезные ссылки

- [GitHub Actions](https://github.com/features/actions)
- [Codecov](https://codecov.io/)
- [Pre-commit](https://pre-commit.com/)
- [Pytest Coverage](https://pytest-cov.readthedocs.io/)

---

**Статус**: 🟡 Настройка завершена, требуется достижение 97% покрытия

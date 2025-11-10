# ✅ Исправления замечаний CodeRabbit для PR #266

## 🔒 Критические исправления безопасности

### 1. ✅ Защита `/debug_env` endpoint (app.py:3164-3180)
**Проблема:** Неаутентифицированный endpoint раскрывал переменные окружения в production.

**Исправление:** Добавлена проверка окружения перед возвратом данных:
```python
# Gate /debug_env to avoid leaking environment details in production
if (
    os.getenv("APP_ENV", "").strip().lower() not in {"", "local", "dev", "development", "test"}
    and os.getenv("PYTEST_CURRENT_TEST") is None
):
    raise HTTPException(status_code=404, detail="Not found")
```

## 🐛 Исправления ошибок

### 2. ✅ Удалены неиспользуемые type: ignore комментарии
- **app/routers/foods.py:37** - удален `# type: ignore[no-any-return]`
- **app/routers/recipes.py:40** - удален `# type: ignore[no-any-return]`

### 3. ✅ Изменен уровень логирования middleware (app.py:424, 427)
**Проблема:** Логирование на уровне INFO засоряло production логи.

**Исправление:** Изменено на DEBUG:
```python
logger.debug("Request: %s %s from %s", request.method, request.url.path, client_host)
logger.debug("Response: %s in %.4fs", response.status_code, process_time)
```

## 🧹 Улучшения качества кода

### 4. ✅ Защита от мутации в `get_recommendations` (core/bayesian_recommendations.py:245-247)
**Проблема:** Функция возвращала внутренний список, который мог быть изменен вызывающим кодом.

**Исправление:** Возвращается копия списка:
```python
if not recommendations:
    return list(fallback)
return list(recommendations)
```

### 5. ✅ PEP 585 compliance (app/services/food_store.py:16, 425)
**Проблема:** Использовался устаревший `Tuple` из typing вместо встроенного `tuple`.

**Исправление:**
- Удален импорт `Tuple`
- Изменен тип возврата: `Tuple[str, float] | None` → `tuple[str, float] | None`

### 6. ✅ Использование `time.perf_counter()` вместо `time.time()` (tests/test_premium_week_hypothesis_simple.py:55, 57)
**Проблема:** `time.time()` может быть подвержен скачкам системных часов.

**Исправление:** Использован монотонный таймер:
```python
start_time = time.perf_counter()
generation_time = time.perf_counter() - start_time
```

### 7. ✅ Улучшен тест `test_get_update_scheduler_without_getter` (tests/test_app_coverage_patch_boost.py:85-99)
**Проблема:** Тавтологическое утверждение `assert scheduler is None or scheduler is not None`.

**Исправление:** Проверка наличия атрибута:
```python
assert scheduler is None or hasattr(scheduler, "get_status")
```

## 🔧 Улучшения скриптов

### 8. ✅ Безопасная замена `eval` на прямой `export` (scripts/claude_login.sh:145)
**Проблема:** Использование `eval` несет риски безопасности.

**Исправление:** Прямой export без eval:
```bash
# Вместо: eval "export $key=$sanitized_value"
export "$key=$value"
```

### 9. ✅ Проверка наличия bash перед синтаксической проверкой (setup_cli_aliases.sh:88-97)
**Проблема:** Скрипт требовал bash без проверки его наличия.

**Исправление:** Добавлена проверка:
```bash
if command -v bash >/dev/null 2>&1; then
    if ! bash -n -c "$expanded_command" >/dev/null 2>&1; then
        echo "syntax error in shell command"
        return 1
    fi
else
    # bash -n not available; skip syntax check (non-fatal)
    :
fi
```

### 10. ✅ Добавлен TODO комментарий для закомментированного алиаса (setup_cli_aliases.sh:247)
**Исправление:** Добавлен комментарий с напоминанием:
```bash
# TODO: Re-enable ppclaude when Claude Code account is restored; verify claude_with_role.sh is available
```

### 11. ✅ Добавлен `--cov-fail-under=97` и установлен cwd (quick_coverage_update.py:41, 54-55)
**Проблема:** Отсутствовал порог покрытия и не был установлен рабочий каталог.

**Исправление:**
- Добавлен `--cov-fail-under=97` в команду pytest
- Установлен `cwd=Path(__file__).parent` для детерминированного разрешения путей

## 📊 Итоговая статистика

- **Критические исправления безопасности:** 1
- **Исправления ошибок:** 2
- **Улучшения качества кода:** 4
- **Улучшения скриптов:** 4

**Всего исправлено:** 11 замечаний CodeRabbit

## ✅ Статус

Все замечания CodeRabbit исправлены. Код готов к коммиту и проверке CI.

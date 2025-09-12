# БЫСТРАЯ ИНСТРУКЦИЯ ПО ПРИМЕНЕНИЮ ИЗМЕНЕНИЙ

## 🚀 ЧТО СДЕЛАТЬ В ПРОЕКТЕ:

### 1. ИЗМЕНИТЬ ОДИН ФАЙЛ:
В файле `providers/ollama.py` строка 13:
```python
# БЫЛО:
timeout_s: float = 30.0

# ИЗМЕНИТЬ НА:
timeout_s: float = 120.0
```

### 2. СОЗДАТЬ 2 НОВЫХ ФАЙЛА:

**A. Файл: `ollama_diagnostic.sh`**
- Скопировать содержимое из CODE_CHANGES.md
- Выполнить: `chmod +x ollama_diagnostic.sh`

**B. Файл: `ollama_monitor.sh`**
- Скопировать содержимое из CODE_CHANGES.md
- Выполнить: `chmod +x ollama_monitor.sh`

### 3. КОМАНДЫ ДЛЯ ТЕСТИРОВАНИЯ:

```bash
# Активация окружения
source .venv/bin/activate

# БЫСТРОЕ ТЕСТИРОВАНИЕ (stub провайдер)
LLM_PROVIDER=stub FEATURE_INSIGHT=1 make run

# ТЕСТ С OLLAMA (медленно, но реально)
LLM_PROVIDER=ollama FEATURE_INSIGHT=1 make run

# ДИАГНОСТИКА OLLAMA
./ollama_diagnostic.sh
```

## ✅ РЕЗУЛЬТАТ:
- ⚡ Быстрое тестирование с stub провайдером
- 🐌 Стабильная работа с Ollama (без таймаутов)
- 🔍 Инструменты диагностики и мониторинга
- 🔄 Легкое переключение между провайдерами

**ВСЕ ГОТОВО ДЛЯ ПРОДОЛЖЕНИЯ РАЗРАБОТКИ!** 🎉

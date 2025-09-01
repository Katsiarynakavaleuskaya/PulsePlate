# КОНКРЕТНЫЕ ИЗМЕНЕНИЯ В КОДЕ

## 1. ИЗМЕНЕННЫЙ ФАЙЛ: providers/ollama.py

**Что изменено:** Увеличен таймаут с 30 до 120 секунд

**БЫЛО:**
```python
def __init__(self, endpoint: str = "http://localhost:11434", model: str = "llama3.1:8b", timeout_s: float = 30.0):
```

**СТАЛО:**
```python
def __init__(self, endpoint: str = "http://localhost:11434", model: str = "llama3.1:8b", timeout_s: float = 120.0):
```

**Причина:** Ollama модели требуют больше времени для холодного старта (2-5 минут)

## 2. НОВЫЕ ФАЙЛЫ

### A. ollama_diagnostic.sh - ДИАГНОСТИЧЕСКИЙ СКРИПТ
**Создать файл:** `/ollama_diagnostic.sh`
**Права:** `chmod +x ollama_diagnostic.sh`

```bash
#!/bin/bash

echo "🔍 Ollama Diagnostic Script"
echo "=========================="
echo "⏰ $(date)"
echo ""

# 1. Проверка процесса
echo "1️⃣ Ollama Process Status:"
if pgrep -f "ollama serve" > /dev/null; then
    echo "✅ Ollama is running (PID: $(pgrep -f "ollama serve"))"
    echo "   Memory usage: $(ps -o pid,rss,pmem,pcpu,command -p $(pgrep -f "ollama serve") | tail -1)"
else
    echo "❌ Ollama is not running"
    exit 1
fi
echo ""

# 2. Проверка API доступности
echo "2️⃣ API Connectivity:"
if curl -s --max-time 3 http://localhost:11434/api/version > /dev/null; then
    VERSION=$(curl -s --max-time 3 http://localhost:11434/api/version | jq -r '.version' 2>/dev/null)
    echo "✅ API is responsive (Version: $VERSION)"
else
    echo "❌ API is not responsive"
fi
echo ""

# 3. Загруженные модели
echo "3️⃣ Loaded Models:"
MODELS=$(curl -s --max-time 5 http://localhost:11434/api/tags | jq -r '.models[].name' 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "$MODELS" | while read model; do
        echo "   📦 $model"
    done
else
    echo "❌ Unable to fetch models"
fi
echo ""

# 4. Тест скорости простого запроса
echo "4️⃣ Response Time Test:"
echo "   Testing with simple prompt..."
START_TIME=$(date +%s)

RESPONSE=$(curl -s --max-time 30 -X POST http://localhost:11434/api/generate \
    -H "Content-Type: application/json" \
    -d '{"model":"llama3.1:8b","prompt":"Hello","stream":false}' 2>/dev/null)

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if [ $? -eq 0 ] && [ ! -z "$RESPONSE" ]; then
    echo "   ✅ Response received in ${DURATION}s"
    RESPONSE_TEXT=$(echo "$RESPONSE" | jq -r '.response' 2>/dev/null | head -c 50)
    echo "   💬 Response: \"$RESPONSE_TEXT...\""
else
    echo "   ❌ Request failed or timed out after ${DURATION}s"
fi
echo ""

# 5. Системные ресурсы
echo "5️⃣ System Resources:"
echo "   CPU Load: $(uptime | awk -F'load average:' '{ print $2 }')"
echo "   Memory: $(free -h 2>/dev/null | grep Mem: || vm_stat | head -2)"
echo "   Disk Space: $(df -h . | tail -1 | awk '{print "Used: "$3"/"$2" ("$5")"}')"
echo ""

echo "🏁 Diagnostic Complete!"
```

### B. ollama_monitor.sh - МОНИТОРИНГ В РЕАЛЬНОМ ВРЕМЕНИ
**Создать файл:** `/ollama_monitor.sh`
**Права:** `chmod +x ollama_monitor.sh`

```bash
#!/bin/bash

# 🔍 Ollama Progress Monitor
# Запускайте этот скрипт в отдельном терминале при работе с Ollama

echo "🔄 Ollama Progress Monitor Started"
echo "================================="
echo "Press Ctrl+C to stop monitoring"
echo ""

LOG_FILE="ollama_monitor.log"
> $LOG_FILE  # Очищаем лог

monitor_process() {
    while true; do
        TIMESTAMP=$(date '+%H:%M:%S')
        
        # CPU и Memory usage процесса Ollama
        OLLAMA_PID=$(pgrep -f "ollama serve")
        if [ ! -z "$OLLAMA_PID" ]; then
            STATS=$(ps -o pid,pcpu,pmem,rss,vsz -p $OLLAMA_PID | tail -1)
            CPU=$(echo $STATS | awk '{print $2}')
            MEM=$(echo $STATS | awk '{print $3}')
            RSS=$(echo $STATS | awk '{print $4}')
            
            # Активность на порту 11434
            CONNECTIONS=$(lsof -i :11434 2>/dev/null | wc -l)
            
            # Логируем и выводим
            LOG_ENTRY="[$TIMESTAMP] CPU: ${CPU}% | MEM: ${MEM}% | RSS: ${RSS}KB | Connections: $CONNECTIONS"
            echo "$LOG_ENTRY"
            echo "$LOG_ENTRY" >> $LOG_FILE
            
            # Если CPU > 50% или MEM > 10% - модель активно работает
            if (( $(echo "$CPU > 50.0" | bc -l 2>/dev/null || echo "0") )); then
                echo "   🔥 HIGH CPU ACTIVITY - Model is processing!"
            elif (( $(echo "$CPU > 10.0" | bc -l 2>/dev/null || echo "0") )); then
                echo "   ⚡ Medium activity"
            else
                echo "   😴 Low activity - idle or waiting"
            fi
        else
            echo "[$TIMESTAMP] ❌ Ollama process not found"
        fi
        
        sleep 2
    done
}

# Trap для корректного завершения
trap 'echo ""; echo "🛑 Monitoring stopped. Log saved to: $LOG_FILE"; exit 0' INT

# Запускаем мониторинг
monitor_process
```

## 3. КОМАНДЫ ДЛЯ НАСТРОЙКИ LLM ПРОВАЙДЕРОВ

### Переключение на STUB (для разработки):
```bash
export LLM_PROVIDER=stub
export FEATURE_INSIGHT=1
make run
```

### Переключение на OLLAMA (для продакшена):
```bash
export LLM_PROVIDER=ollama
export FEATURE_INSIGHT=1
export OLLAMA_ENDPOINT=http://localhost:11434
export OLLAMA_MODEL=llama3.1:8b
make run
```

## 4. ТЕСТОВЫЕ КОМАНДЫ API

### Тест BMI endpoint:
```bash
curl -s -X POST http://127.0.0.1:8001/bmi \
  -H "Content-Type: application/json" \
  -d '{"height_m":1.75,"weight_kg":85,"age":30,"gender":"male","pregnant":"no","athlete":"no","user_group":"general","language":"en"}'
```

### Тест Insight endpoint:
```bash
curl -s -X POST http://127.0.0.1:8001/insight \
  -H "Content-Type: application/json" \
  -d '{"text": "Provide health advice for BMI 27.8"}'
```

### Тест Plan endpoint:
```bash
curl -s -X POST http://127.0.0.1:8001/plan \
  -H "Content-Type: application/json" \
  -d '{"height_m":1.75,"weight_kg":85,"age":30,"gender":"male","pregnant":"no","athlete":"no","user_group":"general","language":"en"}'
```

## 5. ДИАГНОСТИЧЕСКИЕ КОМАНДЫ

```bash
# Активация окружения
source .venv/bin/activate

# Запуск диагностики Ollama
./ollama_diagnostic.sh

# Запуск мониторинга
./ollama_monitor.sh

# Проверка процесса Ollama
ps aux | grep ollama | grep -v grep

# Проверка API Ollama
curl -s http://localhost:11434/api/version

# Остановка приложения
make kill
```

## 6. ОСНОВНЫЕ ВЫВОДЫ

✅ **Ollama холодный старт:** 2-5 минут - это нормально  
✅ **Stub провайдер:** Мгновенные ответы для разработки  
✅ **Переключение провайдеров:** Через переменные среды  
✅ **Мониторинг:** Созданы инструменты диагностики  
✅ **Все endpoints:** Протестированы и работают  

**Проект готов к дальнейшей разработке!**
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
#!/bin/bash

# 🔍 Ollama Progress Monitor
# Запускайте этот скрипт в отдельном терминале при работе с Ollama

echo "🔄 Ollama Progress Monitor Started"
echo "================================="
echo "Press Ctrl+C to stop monitoring"
echo ""

LOG_FILE="ollama_monitor.log"
true > "$LOG_FILE"  # Очищаем лог

monitor_process() {
    while true; do
        TIMESTAMP=$(date '+%H:%M:%S')
        
        # CPU и Memory usage процесса Ollama
        OLLAMA_PID=$(pgrep -f "ollama serve")
        if [ -n "$OLLAMA_PID" ]; then
            STATS=$(ps -o pid,pcpu,pmem,rss,vsz -p "$OLLAMA_PID" | tail -1)
            CPU=$(echo "$STATS" | awk '{print $2}')
            MEM=$(echo "$STATS" | awk '{print $3}')
            RSS=$(echo "$STATS" | awk '{print $4}')
            
            # Активность на порту 11434
            CONNECTIONS=$(lsof -i :11434 2>/dev/null | wc -l)
            
            # Логируем и выводим
            LOG_ENTRY="[$TIMESTAMP] CPU: ${CPU}% | MEM: ${MEM}% | RSS: ${RSS}KB | Connections: $CONNECTIONS"
            echo "$LOG_ENTRY"
            echo "$LOG_ENTRY" >> "$LOG_FILE"
            
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
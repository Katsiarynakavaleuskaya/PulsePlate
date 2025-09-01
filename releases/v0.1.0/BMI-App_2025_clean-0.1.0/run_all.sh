#!/bin/zsh
# 🚀 Автоматический запуск 3-х окон для BMI-App

# === 1. API сервер ===
osascript -e 'tell application "Terminal"
    do script "cd ~/BMI-App_2025_clean && conda activate bmi && uvicorn app:app --host 0.0.0.0 --port 8001 --reload"
end tell'

# === 2. LocalTunnel ===
osascript -e 'tell application "Terminal"
    do script "cd ~/BMI-App_2025_clean && conda activate bmi && npx localtunnel --port 8001 --local-host 127.0.0.1 --print-requests"
end tell'

# === 3. Health-check ===
osascript -e 'tell application "Terminal"
    do script "sleep 5 && curl -s http://127.0.0.1:8001/health"
end tell'

echo "✅ Все три окна запущены!"



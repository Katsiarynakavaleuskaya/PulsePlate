# BMI-App 2025 (FastAPI)

![tests](https://github.com/Katsiarynakavaleuskaya/BMI-App_2025_clean/actions/workflows/python-tests.yml/badge.svg)

## RU

## 🚀 Quick Start / Быстрый старт
```bash
pip install -r requirements.txt

# Запуск API напрямую
uvicorn app:app --host 0.0.0.0 --port 8001
# http://127.0.0.1:8001/health
# http://127.0.0.1:8001/docs
# http://127.0.0.1:8001/redoc

# Альтернативный запуск через Makefile
make dev-all     # поднимает сервер в фоне
make smoke       # локальная проверка health + bmi

# Для внешнего доступа через localtunnel
make tunnel-stop # перезапускает туннель
make tunnel-url  # показывает внешний URL
make smoke-ext   # прогоняет health и bmi через внешний URL


## 🚀 Quick Start

### 1. Локальный запуск (uvicorn)

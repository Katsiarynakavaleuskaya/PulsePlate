FROM python:3.11-slim

# 1) системные обновления (иногда спасает от сетевых/SSL проблем при pip)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    curl ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2) ставим зависимости отдельно (кэшируется)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 3) код
COPY . .

# 4) Hugging Face Spaces передаёт порт через $PORT
#    uvicorn слушает на 0.0.0.0
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT}"]

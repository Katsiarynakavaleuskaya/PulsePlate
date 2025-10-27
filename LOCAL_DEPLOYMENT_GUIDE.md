# 🚀 Локальное развертывание PulsePlate

## 📋 Быстрый старт

### 1. Локальное тестирование (без серверов)

```bash
# Создайте и настройте .env файл
cp .env.example .env
# Отредактируйте .env файл, установив необходимые переменные окружения
# Сохраните изменения

# Запуск приложения локально
docker-compose up -d

# Проверка здоровья
curl http://localhost:8000/health
```

### 2. Настройка тестовых секретов для GitHub Actions

Если у вас пока нет реальных серверов, используйте тестовые значения:

```bash
# Staging (тестовые значения)
gh secret set --env staging SSH_HOST_STAGING --body "localhost"
gh secret set --env staging SSH_USER --body "testuser"
gh secret set --env staging SSH_KEY --body "test-key-content"
gh secret set --env staging STAGING_DOMAIN --body "localhost:8000"

# Production (тестовые значения)
gh secret set --env production SSH_HOST_PRODUCTION --body "localhost"
gh secret set --env production SSH_USER --body "testuser"
gh secret set --env production SSH_KEY --body "test-key-content"
gh secret set --env production PRODUCTION_DOMAIN --body "localhost:8000"
```

### 3. Получение реальных серверов

#### 🆓 Бесплатные варианты

**Railway (рекомендуется):**

1. Зайдите на railway.app
2. Подключите GitHub репозиторий
3. Выберите "Deploy from GitHub repo"
4. Railway автоматически создаст сервер и даст вам URL

**Render:**

1. Зайдите на render.com
2. Создайте "Web Service"
3. Подключите GitHub репозиторий
4. Получите URL вида: `your-app.onrender.com`

**Fly.io:**

1. Установите flyctl: `curl -L https://fly.io/install.sh | sh`
   **⚠️ Внимание**: Перед выполнением команды `curl ... | sh` убедитесь, что доверяете скрипту.
   Рекомендуется проверить URL, документацию или использовать официальные методы установки.
2. Запустите: `fly launch`
3. Получите URL вида: `your-app.fly.dev`

#### 💰 Платные варианты (от $5/месяц)

**DigitalOcean:**

- Droplet от $5/месяц
- Автоматический деплой через GitHub Actions

**Linode:**

- VPS от $5/месяц
- Хорошая документация

**AWS EC2:**

- Free tier на 12 месяцев
- Затем от $3-5/месяц

### 4. Получение домена

#### 🆓 Бесплатные домены

- **Freenom**: .tk, .ml, .ga домены бесплатно
- **No-IP**: бесплатные поддомены

#### 💰 Дешевые домены

- **Namecheap**: от $1/год
- **GoDaddy**: от $2/год
- **Cloudflare**: регистрация доменов

### 5. Настройка SSH ключей

```bash
# Генерация SSH ключа
ssh-keygen -t ed25519 -C "your-email@example.com"

# Копирование публичного ключа на сервер
ssh-copy-id user@your-server-ip

# Использование приватного ключа в GitHub
gh secret set --env staging SSH_KEY --body "$(cat ~/.ssh/id_ed25519)"
# Или безопасный способ - запустите команду и вставьте ключ когда будет запрошено:
# gh secret set --env staging SSH_KEY
```

## 🔧 Пошаговая настройка

### Шаг 1: Создайте сервер

1. Выберите провайдера (Railway/Render/Fly.io)
2. Подключите GitHub репозиторий
3. Получите URL сервера

### Шаг 2: Обновите секреты

```bash
# Замените на ваши реальные значения
gh secret set --env staging SSH_HOST_STAGING --body "your-server-ip"
gh secret set --env staging STAGING_DOMAIN --body "your-app.railway.app"
```

### Шаг 3: Протестируйте развертывание

```bash
# Создайте тестовую ветку для безопасного тестирования
git checkout -b ci-deploy-test

# Создайте тестовый файл вместо изменения README.md
echo "# Test deployment - $(date)" > TEST_DEPLOYMENT.md
git add TEST_DEPLOYMENT.md
git commit -m "test: trigger deployment"
git push origin ci-deploy-test

# После успешного тестирования удалите тестовую ветку
git checkout main
git branch -D ci-deploy-test
git push origin --delete ci-deploy-test
rm TEST_DEPLOYMENT.md
```

## 🎯 Рекомендуемый план действий

1. **Сейчас**: Используйте тестовые значения для проверки CI/CD
2. **Сегодня**: Зарегистрируйтесь на Railway/Render
3. **Завтра**: Настройте реальный сервер и обновите секреты
4. **На выходных**: Купите домен и настроите DNS

## 🆘 Если что-то не работает

1. Проверьте логи GitHub Actions
2. Убедитесь, что секреты правильно настроены
3. Проверьте, что сервер доступен
4. Убедитесь, что SSH ключи корректны

## 📞 Поддержка

Если нужна помощь с настройкой конкретного провайдера - обращайтесь!

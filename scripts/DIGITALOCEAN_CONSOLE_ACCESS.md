# Как попасть в терминал DigitalOcean

## 🎯 Быстрый способ

1. **Зайдите в DigitalOcean Dashboard:**
   - Откройте <https://cloud.digitalocean.com>
   - Войдите в свой аккаунт

2. **Найдите ваш Droplet:**
   - В левом меню нажмите **"Droplets"**
   - Найдите ваш сервер (например, `pulseplate.app` или по IP)

3. **Откройте Console:**
   - Нажмите на имя вашего Droplet
   - В верхней части страницы найдите кнопку **"Console"** или **"Access"** → **"Launch Droplet Console"**
   - Откроется веб-терминал прямо в браузере

4. **Войдите в систему:**
   - Если потребуется логин, используйте:
     - Username: `root` (или ваш пользователь)
     - Password: (пароль root, если не настроен SSH ключ)

## 📋 Пошаговая инструкция с картинками

### Шаг 1: Dashboard → Droplets

```text
DigitalOcean Dashboard
  └─> В левом меню: "Droplets"
      └─> Список ваших серверов
```

### Шаг 2: Выберите ваш Droplet

```text
Список Droplets
  └─> Нажмите на имя вашего сервера
      (например: "pulseplate-production" или IP адрес)
```

### Шаг 3: Откройте Console

На странице Droplet вы увидите несколько вариантов:

#### Вариант A: Кнопка "Console" (в верхней части)

```text
┌─────────────────────────────────────┐
│  [Power] [Console] [Access] [Net...] │
└─────────────────────────────────────┘
```

#### Вариант B: Меню "Access" → "Launch Droplet Console"

```text
Access
  └─> Launch Droplet Console
```

### Шаг 4: Веб-терминал откроется

Откроется окно с терминалом прямо в браузере. Вы увидите приглашение:

```bash
root@pulseplate:~#
```

## ✅ Проверка доступа

После входа выполните:

```bash
# Проверить, что вы на сервере
hostname
whoami
pwd

# Должно показать что-то вроде:
# hostname: pulseplate
# whoami: root
# pwd: /root
```

## 🔧 Выполнение команд на сервере

Теперь вы можете выполнить команды из инструкций:

### 1. Найти deploy директорию

```bash
sudo find / -maxdepth 4 -name "docker-compose.production.yaml" 2>/dev/null
```

### 2. Перейти в найденную директорию

```bash
cd /srv/pulseplate-production  # или найденный путь
```

### 3. Проверить контейнеры

```bash
docker compose -f docker-compose.production.yaml ps
```

### 4. Исправить environment переменные

```bash
# Добавить в .env
echo "APP_ENV=production" >> .env
echo "ENVIRONMENT=production" >> .env

# Перезапустить app
docker compose -f docker-compose.production.yaml up -d --force-recreate app
```

### 5. Переразвернуть Caddy (если нужно)

```bash
# Использовать скрипт (если скопировали на сервер)
bash scripts/redeploy_caddy.sh

# Или вручную (см. deploy/WORKFLOW.md:145 — сначала pull app, затем build caddy)
docker compose -f docker-compose.production.yaml pull app
docker compose -f docker-compose.production.yaml build caddy
docker compose -f docker-compose.production.yaml up -d caddy
docker compose -f docker-compose.production.yaml ps caddy
docker compose -f docker-compose.production.yaml logs --tail=100 caddy
```

## 🚨 Если Console не открывается

1. **Проверьте, что Droplet запущен:**
   - На странице Droplet должна быть зеленая точка "Running"
   - Если нет, нажмите "Power" → "Power On"

2. **Попробуйте другой браузер:**
   - Иногда веб-терминал не работает в некоторых браузерах
   - Попробуйте Chrome, Firefox, Safari

3. **Проверьте JavaScript:**
   - Убедитесь, что JavaScript включен в браузере
   - Отключите блокировщики рекламы для DigitalOcean

4. **Используйте Recovery Console:**
   - Если обычный Console не работает, попробуйте "Recovery Console"
   - Меню "Access" → "Recovery Console"

## 💡 Альтернативные способы доступа

### 1. SSH через другой порт (если настроен)

```bash
# Попробуйте другие порты
ssh -p 2222 root@pulseplate.app
ssh -p 22022 root@pulseplate.app
```

### 2. Self-hosted runner

Если у вас настроен GitHub Actions self-hosted runner на сервере, используйте его для выполнения команд через workflow.

### 3. VNC/Remote Desktop (если установлен)

Если на сервере установлен графический интерфейс, можно использовать VNC.

## 📝 Полезные команды для работы на сервере

```bash
# Проверить статус Docker
docker ps
docker compose ps

# Проверить логи
docker compose logs app
docker compose logs caddy

# Проверить порты
sudo ss -tlnp | grep -E ':(80|443)'

# Проверить environment переменные в контейнере
docker compose exec app env | grep -E 'APP_ENV|ENVIRONMENT|GIT_SHA'

# Проверить health endpoint изнутри Docker сети
docker compose exec caddy wget -qO- http://app:8000/health
```

## 🔐 Безопасность

- **Не делитесь доступом к Console** с другими людьми
- **Используйте сильные пароли** для root (или лучше отключите root и используйте sudo)
- **Настройте SSH ключи** для более безопасного доступа (когда SSH будет доступен)
- **Регулярно обновляйте систему:** `apt update && apt upgrade -y`

## 📚 Дополнительные ресурсы

- [DigitalOcean Documentation: Access Droplet Console](https://docs.digitalocean.com/products/droplets/how-to/connect-with-console/)
- [DigitalOcean Support](https://www.digitalocean.com/support)

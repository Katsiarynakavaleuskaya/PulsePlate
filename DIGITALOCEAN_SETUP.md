# 🌐 DigitalOcean Setup Guide - PulsePlate

## 📋 Быстрый старт

**Стоимость:** $6/месяц (1 vCPU, 1GB RAM)
**Бесплатные кредиты:** $200 для новых пользователей! 🎁
**Ресурсы:** 1 vCPU, 1GB RAM, 25GB SSD, 1TB трафика

---

## Шаг 1: Создание Droplet (сервера)

### 1.1 Вход в панель

1. **Перейдите:** https://cloud.digitalocean.com/
2. Нажмите **"Create"** → **"Droplets"** (или кнопку **"Create Droplet"**)

### 1.2 Выбор образа (Image)

1. **Choose an image:** **Ubuntu**
2. **Version:** **22.04 (LTS)** или **24.04 (LTS)**
   - Рекомендую **22.04 LTS** (стабильнее)

### 1.3 Выбор типа и размера

1. **Choose a plan:** **Regular** (Basic Droplets)
2. **CPU Options:** **Regular with shared CPU**
3. **Plan:** **Basic** → **$6/month**
   - ✅ 1 vCPU
   - ✅ 1 GB RAM
   - ✅ 25 GB SSD
   - ✅ 1 TB transfer

### 1.4 Выбор датацентра

Выберите ближайший регион:
- **Frankfurt** (Германия) - обычно быстрее для РБ
- **Amsterdam** (Нидерланды)
- **London** (Великобритания)

### 1.5 Настройка SSH ключа

**Вариант А: Добавить существующий ключ**

1. Нажмите **"New SSH Key"**
2. **SSH key name:** `pulseplate-deploy`
3. **Public key:** Вставьте содержимое вашего публичного ключа:
   ```bash
   # На локальной машине выполните:
   cat ~/.ssh/pulseplate_deploy.pub
   ```
   Скопируйте весь вывод и вставьте в поле
4. Нажмите **"Add SSH Key"**
5. Выберите этот ключ в списке

**Вариант Б: Создать новый ключ**

1. Выберите **"New SSH Key"** → **"Generate new SSH key pair"**
2. Сохраните приватный ключ, который скачается (заменит `~/.ssh/pulseplate_deploy`)
3. Нажмите **"Add SSH Key"**

### 1.6 Дополнительные настройки

- **Droplet name:** `pulseplate-staging`
- **How many Droplets:** `1`
- **Enable backups:** Отключите (экономия, для staging не обязательно)
- **Enable IPv6:** По желанию
- **Select additional options:** Можно оставить пустым

### 1.7 Создание Droplet

1. Нажмите **"Create Droplet"**
2. Подождите 1-2 минуты, пока Droplet создается
3. После создания вы увидите:
   - **IPv4 address** (публичный IP) - **СОХРАНИТЕ ЕГО!**
   - **IPv6 address** (если включен)

---

## Шаг 2: Получение IP адреса

1. В панели DigitalOcean найдите ваш Droplet `pulseplate-staging`
2. Скопируйте **IPv4 address** (например: `123.45.67.89`)
3. Этот IP нужно будет добавить в DuckDNS

---

## Шаг 3: Подключение по SSH

### 3.1 Первое подключение

```bash
# Замените IP на ваш публичный IP из DigitalOcean
ssh -i ~/.ssh/pulseplate_deploy root@YOUR_PUBLIC_IP

# Если при создании выбрали другой пользователь, используйте:
ssh -i ~/.ssh/pulseplate_deploy ubuntu@YOUR_PUBLIC_IP
```

**Примечание:** По умолчанию DigitalOcean создает сервер с пользователем `root`.

### 3.2 Базовая настройка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
sudo apt install -y docker.io docker-compose-plugin

# Проверка Docker (root пользователь может использовать docker напрямую)
docker --version
docker compose version
```

Если хотите использовать пользователя `ubuntu` вместо `root`:

```bash
# Создание пользователя ubuntu
adduser ubuntu
usermod -aG sudo ubuntu
mkdir -p /home/ubuntu/.ssh
cp ~/.ssh/authorized_keys /home/ubuntu/.ssh/
chown -R ubuntu:ubuntu /home/ubuntu/.ssh
chmod 700 /home/ubuntu/.ssh
chmod 600 /home/ubuntu/.ssh/authorized_keys

# Добавление в группу docker
usermod -aG docker ubuntu

# Выход
exit
```

Подключитесь как ubuntu:

```bash
ssh -i ~/.ssh/pulseplate_deploy ubuntu@YOUR_PUBLIC_IP
newgrp docker  # Применяем группу docker
```

### 3.3 Проверка Docker

```bash
docker --version
docker compose version
```

Должны увидеть версии Docker и Docker Compose.

---

## Шаг 4: Настройка DuckDNS

1. **Войдите в DuckDNS:** https://www.duckdns.org/login
2. **Откройте домен:** `pulseplate-staging`
3. **Обновите IP адрес:**
   - Вставьте ваш **публичный IP** из DigitalOcean
   - Нажмите **"update ip"**

**Результат:** `pulseplate-staging.duckdns.org` теперь указывает на ваш сервер

---

## Шаг 5: Проверка SSH подключения

С локальной машины попробуйте подключиться:

```bash
ssh -i ~/.ssh/pulseplate_deploy root@YOUR_PUBLIC_IP
# или
ssh -i ~/.ssh/pulseplate_deploy ubuntu@YOUR_PUBLIC_IP
```

Если подключились без пароля — всё настроено правильно! ✅

---

## Шаг 6: Обновление GitHub Secrets

После настройки сервера обновите GitHub Secrets:

### Staging Environment:

1. GitHub → **Settings** → **Environments** → **staging**
2. Добавьте/обновите секреты:

| Secret Name | Value |
|------------|-------|
| `STAGING_DOMAIN` | `pulseplate-staging.duckdns.org` |
| `SSH_HOST_STAGING` | `ВАШ_ПУБЛИЧНЫЙ_IP_ИЗ_DIGITALOCEAN` |
| `SSH_USER` | `root` (или `ubuntu`, если создали) |
| `SSH_KEY` | Весь приватный ключ из `~/.ssh/pulseplate_deploy` |
| `GHCR_READ_TOKEN` | GitHub PAT token (см. `GITHUB_SECRETS_SETUP.md`) |

---

## Шаг 7: Базовая безопасность

```bash
# На сервере
sudo apt install -y ufw fail2ban

# Настройка firewall
sudo ufw allow ssh
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw --force enable

# Проверка
sudo ufw status
```

---

## 💰 Стоимость и бесплатные кредиты

- **Basic Droplet:** $6/месяц
- **Бесплатные кредиты:** $200 (новым пользователям)
- **Покрывает:** ~33 месяца использования ($200 ÷ $6 = 33.3 месяца)

**Как использовать кредиты:**
- Кредиты применяются автоматически к счету
- Не нужно ничего активировать
- Проверьте баланс: https://cloud.digitalocean.com/account/billing

---

## 🔗 Полезные ссылки

- **DigitalOcean Console:** https://cloud.digitalocean.com/
- **Droplets:** https://cloud.digitalocean.com/droplets
- **Billing:** https://cloud.digitalocean.com/account/billing
- **Документация:** https://docs.digitalocean.com/

---

## ❓ Troubleshooting

### Не могу подключиться по SSH

1. Проверьте, что SSH ключ выбран при создании Droplet
2. Проверьте права на ключ: `chmod 600 ~/.ssh/pulseplate_deploy`
3. Убедитесь, что используете правильного пользователя (`root` по умолчанию)

### Как проверить баланс кредитов

1. Перейдите: https://cloud.digitalocean.com/account/billing
2. Посмотрите раздел **"Account Credits"**

---

## 📚 Следующие шаги

После настройки сервера:
1. ✅ Сервер создан и доступен
2. ✅ SSH настроен
3. ✅ DuckDNS указывает на сервер
4. ✅ GitHub Secrets обновлены
5. ➡️ См. `DEPLOYMENT_FULL_GUIDE.md` для настройки деплоя

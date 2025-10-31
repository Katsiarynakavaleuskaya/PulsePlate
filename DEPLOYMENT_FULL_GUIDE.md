# 🚀 Полная инструкция по деплою PulsePlate - Для новичков

**Для кого:** Если вы делаете деплой в первый раз
**Время:** ~2-3 часа на полную настройку
**Сложность:** Пошагово, с объяснениями

---

## 📚 Что нужно прочитать (в каком порядке)

### 🎯 Шаг 1: Общий обзор (5 минут)
**Файл:** `SOLO_DEPLOYMENT_SETUP.md`
- Что такое staging и production
- Какие домены мы используем
- Что нужно будет настроить

### 🌐 Шаг 2: Домены (30 минут)
**Файл:** `DOMAIN_SETUP.md`
- Регистрация на Cloudflare (production домен)
- Регистрация на DuckDNS (staging домен)
- Настройка DNS записей

### 🔒 Шаг 3: Безопасность Cloudflare (20 минут)
**Файл:** `CLOUDFLARE_SECURITY_SETUP.md`
- Включение SSL/TLS (Full strict)
- Настройка HSTS
- Включение WAF и Rate Limiting

### 💻 Шаг 4: Настройка сервера (60-90 минут)
**Файлы:**
- `STAGING_SETUP.md` — для staging сервера
- `PRODUCTION_SETUP.md` — для production сервера
- Установка Docker, настройка безопасности (UFW, fail2ban, SSH)

### 🔐 Шаг 5: GitHub Secrets (30 минут)
**Файл:** `GITHUB_SECRETS_SETUP.md`
- Создание SSH ключей
- Генерация GitHub токенов
- Добавление секретов в GitHub Environments

### ⚙️ Шаг 6: Проверка и первый деплой (30 минут)
- Push в main → проверка staging
- Создание tag v1.0.0 → проверка production

---

## 🎓 Пошаговая инструкция (детально)

### Подготовка (что нужно иметь)

✅ Аккаунт на GitHub
✅ VPS/сервер (например, DigitalOcean, Hetzner, AWS) с Ubuntu
✅ ~$7 для покупки домена на год
✅ 2-3 часа свободного времени

---

## Часть 1: Регистрация доменов

### 1.1 Production домен (Cloudflare)

**Что делать:**

1. Откройте: https://dash.cloudflare.com/sign-up
2. Зарегистрируйтесь (email + пароль)
3. После входа нажмите **Registrar** → **Search**
4. Найдите свободный домен: `pulseplate.app` (или другой, который вам нравится)
5. Добавьте в корзину и оплатите (~$7/год)

**Важно:** После покупки домен автоматически будет в вашем аккаунте Cloudflare — никаких дополнительных настроек DNS пока не нужно.

**Результат:** У вас есть домен `pulseplate.app` (или выбранный вами)

### 1.2 Staging домен (DuckDNS)

**Что делать:**

1. Откройте: https://www.duckdns.org
2. Нажмите **Sign in** и войдите через **GitHub** (или Google)
3. После входа вы увидите форму **Add Domain**
4. Введите: `pulseplate-staging` (без `.duckdns.org`)
5. Нажмите **Add Domain**

**Результат:** У вас есть поддомен `pulseplate-staging.duckdns.org`

**Пока не добавляйте IP адрес** — это сделаем после настройки сервера.

---

## Часть 2: Настройка сервера (VPS)

### 2.1 Подключение к серверу

**Если у вас есть сервер:**

```bash
# Подключитесь по SSH (замените IP на ваш)
ssh root@YOUR_SERVER_IP
# Или если используете другого пользователя:
ssh ubuntu@YOUR_SERVER_IP
```

**Если сервера нет:**

Рекомендуемые провайдеры:
- **DigitalOcean**: https://www.digitalocean.com (от $6/месяц)
- **Hetzner**: https://www.hetzner.com (от €4/месяц)
- **AWS Lightsail**: https://aws.amazon.com/lightsail (от $5/месяц)

Создайте Ubuntu 22.04 или 24.04 сервер с минимум 2GB RAM.

### 2.2 Базовая настройка сервера

**Выполните эти команды на сервере (последовательно):**

```bash
# 1. Обновление системы
sudo apt update && sudo apt upgrade -y

# 2. Установка Docker
sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER

# 3. Выход и повторный вход (чтобы применить группу docker)
exit
# Подключитесь снова:
ssh user@YOUR_SERVER_IP

# 4. Проверка Docker
docker --version
docker compose version
```

**Результат:** Docker установлен и работает

### 2.3 Безопасность сервера (обязательно!)

**Это защитит ваш сервер от атак:**

```bash
# 1. Установка UFW (firewall) и fail2ban
sudo apt install -y ufw fail2ban unattended-upgrades

# 2. Настройка UFW (firewall)
sudo ufw allow ssh
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw --force enable

# 3. Проверка статуса firewall
sudo ufw status

# 4. Настройка fail2ban (защита от брутфорса SSH)
sudo tee /etc/fail2ban/jail.local > /dev/null << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
EOF

sudo systemctl enable --now fail2ban

# 5. Жёсткая настройка SSH (отключение паролей, только ключи)
sudo tee -a /etc/ssh/sshd_config > /dev/null << 'EOF'

# Security hardening
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
X11Forwarding no
EOF

# Проверка конфигурации SSH перед перезапуском
sudo sshd -t && sudo systemctl restart sshd

# 6. Включение автоматических обновлений безопасности
sudo dpkg-reconfigure -plow unattended-upgrades
```

**⚠️ ВАЖНО:** После этих настроек вы сможете подключаться только по SSH ключу, а не по паролю. Убедитесь, что ваш SSH ключ уже добавлен на сервер!

**Результат:** Сервер защищён от базовых атак

### 2.4 Создание директорий для приложения

```bash
# Создаём директории для production
sudo mkdir -p /srv/pulseplate-production
sudo chown $USER:$USER /srv/pulseplate-production

# Создаём директории для staging (если нужен отдельный сервер)
# sudo mkdir -p /srv/pulseplate-staging
# sudo chown $USER:$USER /srv/pulseplate-staging
```

**Результат:** Готовы директории для файлов приложения

---

## Часть 3: Настройка Cloudflare

### 3.1 Настройка DNS в Cloudflare

**Что делать:**

1. Откройте: https://dash.cloudflare.com
2. Выберите ваш домен `pulseplate.app`
3. Перейдите в **DNS** → **Records**
4. Нажмите **Add record**:
   - **Type**: A
   - **Name**: `@` (или оставьте пустым — это корневой домен)
   - **IPv4 address**: `YOUR_SERVER_IP` (IP вашего сервера)
   - **Proxy status**: **Proxied** (оранжевое облако) ✅
   - Нажмите **Save**

5. Добавьте запись для `www` (опционально):
   - **Type**: A
   - **Name**: `www`
   - **IPv4 address**: `YOUR_SERVER_IP`
   - **Proxy status**: **Proxied** ✅
   - Нажмите **Save**

**Результат:** DNS записи настроены, домен указывает на ваш сервер

### 3.2 Настройка SSL/TLS

**Что делать:**

1. В Cloudflare Dashboard → ваш домен → **SSL/TLS**
2. **Overview**:
   - **SSL/TLS encryption mode**: Выберите **Full (strict)** ✅
3. **Edge Certificates**:
   - ✅ **Always Use HTTPS**: Включить
   - ✅ **Automatic HTTPS Rewrites**: Включить
   - ✅ **Opportunistic Encryption**: Включить

**Результат:** SSL/TLS настроен, сайт будет работать по HTTPS

### 3.3 Настройка HSTS

**Что делать:**

1. **SSL/TLS** → **Edge Certificates** → **HTTP Strict Transport Security (HSTS)**
2. Нажмите **Enable HSTS**
3. Настройки:
   - **Max Age**: `6 months`
   - ✅ **Include SubDomains**
   - ✅ **Preload** (опционально)
4. Нажмите **Save**

**Результат:** Браузеры будут всегда использовать HTTPS для вашего домена

### 3.4 Включение WAF (защита от атак)

**Что делать:**

1. **Security** → **WAF**
2. Убедитесь, что WAF включён (кнопка должна быть ON)
3. Перейдите в **Managed Rules**:
   - ✅ **Cloudflare Managed Ruleset** должен быть включён

**Результат:** Базовая защита от веб-атак включена

### 3.5 Rate Limiting (защита API от перегрузки)

**Что делать:**

1. **Security** → **WAF** → **Rate limiting rules**
2. Нажмите **Create rule**
3. Заполните:
   - **Rule name**: `API Rate Limit`
   - **Rule expression**:
     ```
     (http.request.uri.path contains "/api/v1/admin/" or http.request.uri.path contains "/api/v1/premium/")
     ```
   - **Threshold**:
     - Requests: `10`
     - Period: `1 minute`
   - **Action**: `Block`
4. Нажмите **Save**

**Результат:** Admin и premium endpoints защищены от перегрузки

### 3.6 Bot Fight Mode (защита от ботов)

**Что делать:**

1. **Security** → **Bots**
2. **Bot Fight Mode**: Включите (ON)

**Результат:** Простые боты будут блокироваться

---

## Часть 4: Настройка DuckDNS (Staging)

### 4.1 Обновление IP в DuckDNS

**Что делать:**

1. Откройте: https://www.duckdns.org
2. Войдите в аккаунт
3. Найдите ваш поддомен `pulseplate-staging`
4. В поле **IPv4** введите IP вашего сервера
5. Нажмите **update ip**

**Результат:** `pulseplate-staging.duckdns.org` теперь указывает на ваш сервер

---

## Часть 5: Настройка GitHub Secrets

### 5.1 Создание SSH ключа

**Выполните на вашем локальном компьютере:**

```bash
# Генерируем SSH ключ
ssh-keygen -t ed25519 -C "pulseplate-deploy" -f ~/.ssh/pulseplate_deploy

# Если ed25519 не поддерживается:
# ssh-keygen -t rsa -b 4096 -C "pulseplate-deploy" -f ~/.ssh/pulseplate_deploy

# Нажмите Enter на всех вопросах (можно установить пароль, но не обязательно)
```

**Результат:** Созданы два файла:
- `~/.ssh/pulseplate_deploy` (приватный ключ — НИКОГДА никому не показывайте!)
- `~/.ssh/pulseplate_deploy.pub` (публичный ключ — можно показывать)

### 5.2 Добавление SSH ключа на сервер

```bash
# Показываем публичный ключ
cat ~/.ssh/pulseplate_deploy.pub

# Скопируйте весь вывод (начинается с ssh-ed25519 или ssh-rsa)
```

**Теперь на сервере:**

```bash
# Подключитесь к серверу
ssh user@YOUR_SERVER_IP

# Создаём директорию для ключей (если нет)
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Добавляем ваш публичный ключ
nano ~/.ssh/authorized_keys
# Вставьте скопированный публичный ключ в новую строку
# Сохраните: Ctrl+O, Enter, Ctrl+X

# Устанавливаем правильные права
chmod 600 ~/.ssh/authorized_keys
```

**Проверка:**

```bash
# На локальном компьютере попробуйте подключиться
ssh -i ~/.ssh/pulseplate_deploy user@YOUR_SERVER_IP
# Должно подключиться БЕЗ запроса пароля
```

**Результат:** Вы можете подключаться к серверу по SSH ключу

### 5.3 Создание GitHub Personal Access Token

**Что делать:**

1. Откройте: https://github.com/settings/tokens?type=beta
2. Нажмите **Generate new token** → **Generate new token (classic)**
3. Заполните:
   - **Note**: `PulsePlate GHCR Read Token`
   - **Expiration**: Выберите срок (рекомендую `90 days` или `No expiration`)
   - **Select scopes**: Отметьте ТОЛЬКО `read:packages` ✅
4. Нажмите **Generate token** внизу страницы
5. **ВАЖНО:** Скопируйте токен СРАЗУ (он начинается с `ghp_...`) — он больше не будет показан!

**Результат:** У вас есть GitHub токен с правами на чтение пакетов

### 5.4 Добавление секретов в GitHub

**Что делать:**

1. Откройте: https://github.com/Katsiarynakavaleuskaya/PulsePlate/settings/environments
2. Если environments нет, создайте их:
   - Нажмите **New environment**
   - Введите `staging` → **Configure environment**
   - Нажмите **Save protection rules** (можно оставить пустым)
   - Повторите для `production`

3. **Для `staging` environment:**
   - Нажмите на `staging` → **Add secret**
   - Добавьте каждый секрет:

     ```
     Name: STAGING_DOMAIN
     Value: pulseplate-staging.duckdns.org
     ```

     ```
     Name: SSH_HOST_STAGING
     Value: YOUR_SERVER_IP (или домен, например staging.yourdomain.com)
     ```

     ```
     Name: SSH_USER
     Value: ubuntu (или root, в зависимости от вашего сервера)
     ```

     ```
     Name: SSH_KEY
     Value: [вставьте весь приватный ключ из ~/.ssh/pulseplate_deploy]
     ```

     Чтобы получить приватный ключ:
     ```bash
     cat ~/.ssh/pulseplate_deploy
     ```
     Скопируйте ВСЁ, включая строки `-----BEGIN OPENSSH PRIVATE KEY-----` и `-----END OPENSSH PRIVATE KEY-----`

     ```
     Name: GHCR_READ_TOKEN
     Value: [вставьте GitHub токен, который вы создали]
     ```

4. **Для `production` environment:**
   - Повторите те же шаги, но используйте:
     ```
     Name: PRODUCTION_DOMAIN
     Value: pulseplate.app (или ваш домен)

     Name: SSH_HOST_PRODUCTION
     Value: YOUR_SERVER_IP
     ```

**Результат:** Все секреты добавлены в GitHub

---

## Часть 6: Первый деплой

### 6.1 Проверка перед деплоем

**Убедитесь:**
- ✅ Домены зарегистрированы
- ✅ DNS записи настроены (Cloudflare + DuckDNS)
- ✅ Сервер настроен (Docker установлен, безопасность включена)
- ✅ GitHub Secrets добавлены

### 6.2 Тестовый деплой на Staging

**Что делать:**

1. Убедитесь, что все изменения закоммичены:
   ```bash
   git add .
   git commit -m "Setup deployment configuration"
   ```

2. Push в main branch:
   ```bash
   git push origin main
   ```

3. Откройте GitHub Actions:
   - https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions
   - Найдите запущенный workflow "CD"
   - Дождитесь завершения (должен собрать Docker образ)

4. После успешной сборки проверьте:
   ```bash
   curl https://pulseplate-staging.duckdns.org/health
   # Должен вернуть: {"status":"ok"}
   ```

**Результат:** Staging работает!

### 6.3 Production деплой

**Что делать:**

1. Создайте release tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. GitHub Actions автоматически запустит production build

3. После успешной сборки проверьте:
   ```bash
   curl https://pulseplate.app/health
   # Должен вернуть: {"status":"ok"}
   ```

**Результат:** Production работает!

---

## 🔍 Проверка безопасности

### Проверка SSL/TLS

```bash
# Проверка сертификата
curl -I https://pulseplate.app/health | grep -i "strict-transport"

# Должен быть заголовок: Strict-Transport-Security
```

### Проверка fail2ban

```bash
# На сервере
ssh user@YOUR_SERVER_IP
sudo fail2ban-client status sshd
# Должен показать статистику блокировок
```

---

## ❓ Частые проблемы и решения

### Проблема: "SSH connection refused"

**Решение:**
- Проверьте, что порт 22 открыт в firewall сервера
- Убедитесь, что SSH ключ добавлен в `~/.ssh/authorized_keys` на сервере

### Проблема: "Domain not resolving"

**Решение:**
- Проверьте DNS записи в Cloudflare/DuckDNS
- Подождите 5-60 минут для распространения DNS
- Проверьте: `nslookup pulseplate.app` или `dig pulseplate.app`

### Проблема: "Docker build failed"

**Решение:**
- Проверьте логи в GitHub Actions
- Убедитесь, что Dockerfile корректен
- Проверьте, что все зависимости указаны в requirements.txt

### Проблема: "Health check failed"

**Решение:**
- Проверьте, что приложение запущено на сервере
- Проверьте логи контейнера: `docker logs <container_name>`
- Убедитесь, что порт 8000 доступен

---

## 📝 Чеклист готовности

Перед первым деплоем убедитесь:

- [ ] Production домен куплен (Cloudflare)
- [ ] Staging домен создан (DuckDNS)
- [ ] DNS записи настроены (A-записи с проксированием)
- [ ] SSL/TLS настроен в Cloudflare (Full strict)
- [ ] HSTS включён
- [ ] WAF включён
- [ ] Сервер настроен (Docker, UFW, fail2ban, SSH hardening)
- [ ] SSH ключ создан и добавлен на сервер
- [ ] GitHub PAT токен создан (read:packages)
- [ ] Все секреты добавлены в GitHub Environments
- [ ] Тестовый деплой на staging успешен
- [ ] Health check возвращает 200

---

## 🎉 Готово!

После выполнения всех шагов:
- ✅ Staging автоматически обновляется при push в `main`
- ✅ Production обновляется при создании tag `v*`
- ✅ Сервер защищён базовыми мерами безопасности
- ✅ Домены настроены с SSL/TLS

**Следующие шаги:**
- Регулярно проверяйте логи приложения
- Делайте бэкапы базы данных
- Обновляйте зависимости раз в месяц
- Следите за уведомлениями Cloudflare

---

## 📚 Дополнительные файлы (для углубления)

- `STAGING_SETUP.md` — детальная настройка staging окружения
- `PRODUCTION_SETUP.md` — детальная настройка production окружения
- `CLOUDFLARE_SECURITY_SETUP.md` — детальная настройка безопасности Cloudflare
- `GITHUB_SECRETS_SETUP.md` — детальная настройка секретов

---

**Вопросы?** Проверьте логи GitHub Actions или раздел "Частые проблемы" выше.

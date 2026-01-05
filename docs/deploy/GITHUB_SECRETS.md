# 🔐 Настройка GitHub Secrets для PulsePlate

## 📍 Где добавить секреты

### Шаг 1: Создание Environments

1. Откройте репозиторий на GitHub: [https://github.com/Katsiarynakavaleuskaya/PulsePlate](https://github.com/Katsiarynakavaleuskaya/PulsePlate)
2. Перейдите: **Settings** → **Environments** (в левом меню)
3. Создайте два environment:
   - `staging` (для main branch)
   - `production` (для tags v*)

## 🔗 Ссылки для регистрации

### 1. Cloudflare Registrar (Production домен ~$7/год)

**Ссылки:**
- Регистрация: [https://dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up)
- Регистрация домена: [https://dash.cloudflare.com/registrar/search](https://dash.cloudflare.com/registrar/search)
- Документация: [https://developers.cloudflare.com/registrar/get-started/register-domain/](https://developers.cloudflare.com/registrar/get-started/register-domain/)

**Шаги:**
1. Зарегистрируйтесь/войдите на Cloudflare
2. Перейдите в **Registrar** → **Search**
3. Найдите свободный домен (например: `pulseplate.app`)
4. Добавьте в корзину и оплатите (~$7/год для `.app`)
5. После покупки домен автоматически будет в вашем аккаунте Cloudflare

### 2. DuckDNS (Staging домен - бесплатно)

**Ссылки:**
- Главная: [https://www.duckdns.org](https://www.duckdns.org)
- Вход через GitHub: [https://www.duckdns.org/login](https://www.duckdns.org/login)

**Шаги:**
1. Нажмите **Sign in** и войдите через GitHub (или другой OAuth провайдер)
2. После входа нажмите **Add Domain**
3. Введите имя поддомена: `pulseplate-staging`
4. Нажмите **Add Domain**
5. Запишите ваш полный домен: `pulseplate-staging.duckdns.org`
6. Добавьте IP вашего сервера в поле **IP Addresses** (если знаете) или оставьте пустым для автообновления

### 3. TON Cloud / Pavel Durov Platform (будущая платформа)

**Полезные ссылки:**
- TON Blockchain: [https://ton.org](https://ton.org)
- TON Developer Docs: [https://docs.ton.org](https://docs.ton.org)
- TON Cloud (если доступен): [https://cloud.ton.org](https://cloud.ton.org)

**Примечание:** На момент 2025 года Павел Дуров анонсировал развитие инфраструктуры TON для децентрализованных приложений. Для веб-приложений (FastAPI) эта платформа может быть доступна позже. Следите за обновлениями на официальных каналах TON.

## 🔑 Секреты для GitHub Environments

### Staging Environment (`staging`)

Добавьте в GitHub → Settings → Environments → `staging` → **Secrets**:

| Secret Name | Описание | Пример значения | Где получить |
|------------|----------|----------------|--------------|
| `STAGING_DOMAIN` | Домен для staging | `pulseplate-staging.duckdns.org` | После регистрации на DuckDNS |
| `SSH_HOST_STAGING` | IP адрес или домен staging сервера | `123.45.67.89` или `staging.example.com` | IP вашего VPS/сервера |
| `SSH_USER` | SSH username | `ubuntu` или `root` | Зависит от вашего сервера |
| `SSH_KEY` | Приватный SSH ключ | `-----BEGIN OPENSSH PRIVATE KEY-----...` | См. раздел "Генерация SSH ключей" ниже |  # pragma: allowlist secret
| `GHCR_READ_TOKEN` | GitHub Personal Access Token для чтения пакетов | `ghp_xxxxxxxxxxxxx` | См. раздел "GitHub Token" ниже |  # pragma: allowlist secret

### Production Environment (`production`)

Добавьте в GitHub → Settings → Environments → `production` → **Secrets**:

| Secret Name | Описание | Пример значения | Где получить |
|------------|----------|----------------|--------------|
| `PRODUCTION_DOMAIN` | Домен для production | `pulseplate.app` | После регистрации на Cloudflare |
| `SSH_HOST_PRODUCTION` | IP адрес или домен production сервера | `123.45.67.89` или `prod.example.com` | IP вашего VPS/сервера |
| `SSH_USER` | SSH username (можно переиспользовать из staging) | `ubuntu` или `root` | Зависит от вашего сервера |
| `SSH_KEY` | Приватный SSH ключ (можно тот же) | `-----BEGIN OPENSSH PRIVATE KEY-----...` | См. раздел "Генерация SSH ключей" ниже |  # pragma: allowlist secret
| `GHCR_READ_TOKEN` | GitHub Personal Access Token | `ghp_xxxxxxxxxxxxx` | См. раздел "GitHub Token" ниже |

## 🔐 Генерация SSH ключей

### 1. Создание SSH ключевой пары (на локальной машине)

```bash
# Генерируем новый SSH ключ
ssh-keygen -t ed25519 -C "github-actions-pulseplate" -f ~/.ssh/pulseplate_deploy

# Или если ed25519 не поддерживается:
ssh-keygen -t rsa -b 4096 -C "github-actions-pulseplate" -f ~/.ssh/pulseplate_deploy
```

### 2. Добавление публичного ключа на сервер

```bash
# Скопируйте публичный ключ
cat ~/.ssh/pulseplate_deploy.pub

# Подключитесь к серверу и добавьте ключ
ssh user@your-server-ip
mkdir -p ~/.ssh
echo "ВАШ_ПУБЛИЧНЫЙ_КЛЮЧ" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

### 3. Добавление приватного ключа в GitHub Secrets

```bash
# Покажите приватный ключ (скопируйте весь вывод)
cat ~/.ssh/pulseplate_deploy

# Или на Windows (PowerShell):
Get-Content ~/.ssh/pulseplate_deploy
```

**Важно:**
- Копируйте ВЕСЬ ключ, включая строки `-----BEGIN OPENSSH PRIVATE KEY-----` и `-----END OPENSSH PRIVATE KEY-----`  # pragma: allowlist secret
- Добавьте его как значение секрета `SSH_KEY` в оба environment (staging и production)

## 🎫 GitHub Personal Access Token (PAT)

### Создание токена для GHCR (GitHub Container Registry)

1. Перейдите: [https://github.com/settings/tokens?type=beta](https://github.com/settings/tokens?type=beta)
2. Нажмите **Generate new token** → **Generate new token (classic)**
3. Настройки:
   - **Note**: `PulsePlate GHCR Read Token`
   - **Expiration**: Выберите срок действия (рекомендуется 90 дней для production, не используйте `No expiration`). Для staging можно использовать 30 дней.
   - **Scopes**: Отметьте `read:packages`
4. Нажмите **Generate token**
5. **ВАЖНО:** Скопируйте токен сразу (он больше не будет показан!)
6. Добавьте как `GHCR_READ_TOKEN` в оба environment

## 📝 Пошаговая инструкция добавления секретов

### Для Staging:

1. GitHub → **Settings** → **Environments** → нажмите `staging` (или создайте новый)
2. В разделе **Environment secrets** нажмите **Add secret**
3. Добавьте каждый секрет:
   ```text
   Name: STAGING_DOMAIN
   Value: pulseplate-staging.duckdns.org
   ```
   Повторите для всех секретов из таблицы выше.

### Для Production:

1. GitHub → **Settings** → **Environments** → нажмите `production` (или создайте новый)
2. В разделе **Environment secrets** нажмите **Add secret**
3. Добавьте каждый секрет:
   ```text
   Name: PRODUCTION_DOMAIN
   Value: pulseplate.app
   ```
   Повторите для всех секретов.

## ✅ Проверка настройки

После добавления всех секретов:

1. Проверьте, что environments созданы: **Settings** → **Environments**
2. Убедитесь, что секреты добавлены (они будут показаны как `●●●●●●●●`)
3. Push в main branch должен запустить staging build
4. Создание tag `v1.0.0` должно запустить production build

## 🔄 Обновление секретов

Если нужно изменить секрет:
1. GitHub → **Settings** → **Environments** → выберите environment
2. Найдите секрет в списке
3. Нажмите **Update** (карандаш) и введите новое значение

## ⚠️ Важные замечания

### Общие правила

- **Никогда** не коммитьте секреты в Git
- **Required reviewers** для production можно оставить пустым или установить 1 (самого себя), если работаете одна
- Для соло-разработки можно использовать один SSH ключ для staging и production (для production рекомендуется отдельные ключи)

### Управление SSH ключами

- **Production:** Используйте отдельные SSH ключи для staging и production
- **Passphrase:** Всегда защищайте приватные ключи паролем (passphrase) при локальном хранении
- **Agent forwarding:** Отключайте SSH agent forwarding в GitHub Actions (установите `ForwardAgent no` в конфигурации)
- **Ротация:** Ревокируйте и обновляйте ключи при подозрении на компрометацию или каждые 180 дней (production)

### Настройка файрвола

- **UFW/Security Groups:** Ограничьте открытые порты только необходимыми (обычно 22 для SSH, 80/443 для HTTP/HTTPS)
- **SSH по IP:** Ограничьте SSH доступ по IP-адресам через UFW (`ufw allow from YOUR_IP to any port 22`) или Security Groups
- **Базовые правила:** Закройте все порты по умолчанию, затем открывайте только нужные

### HTTPS/SSL

- **ACME/Let's Encrypt:** Используйте доверенный CA (например, Let's Encrypt через certbot) для автоматического получения сертификатов
- **HSTS:** Включите HTTP Strict Transport Security в заголовках (Cloudflare автоматически настраивает при Full SSL)
- **Валидация:** Настройте автоматическую проверку сертификатов и мониторинг срока действия
- **Автообновление:** Настройте автоматическое обновление сертификатов через cron или systemd timer

### Аудит и логирование

- **Audit daemon:** Включите `auditd` (Linux) или эквивалент для отслеживания системных событий
- **Централизация логов:** Настройте централизованное хранение логов (rsyslog, journald forwarding) для production
- **Хранение:** Установите политику хранения логов (минимум 90 дней для production)
- **Алерты:** Настройте уведомления на подозрительную активность (множественные неудачные SSH-попытки, изменения конфигурации)

### Ротация токенов и хранение секретов

- **Токены:** Ротируйте GitHub PAT токены каждые 90 дней для production (30 дней для staging). Используйте конечные сроки действия (90 дней), не устанавливайте `No expiration` для production токенов.
- **Процесс ротации:**
  1. **Планирование:** Установите календарное напоминание за 7 дней до истечения токена (для production — каждые 83 дня, для staging — каждые 23 дня)
  2. **Автоматизация:** Настройте CI/CD workflow или скрипт для проверки истечения токенов (например, GitHub Actions workflow с проверкой через GitHub API)
  3. **Резервный план:** Документируйте шаги экстренной ротации и отзыва токенов на случай компрометации:
     - Отзовите токен немедленно: GitHub → Settings → Developer settings → Personal access tokens → Revoke
     - Создайте новый токен с теми же правами
     - Обновите секреты в GitHub Environments (staging/production)
     - Проверьте логи для подозрительной активности
  4. **Ресурсы:** См. [GitHub PAT Rotation Best Practices](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) и [Token Rotation Guide](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/token-expiration-and-rotation)
- **Secrets Manager:** Для production используйте менеджер секретов (HashiCorp Vault, AWS Secrets Manager) вместо прямого хранения в GitHub Secrets
- **Доступ:** Минимизируйте количество людей с доступом к секретам, используйте принцип наименьших привилегий

### Минимальная безопасность (соло-разработка)

- На сервере: `PasswordAuthentication no` в `/etc/ssh/sshd_config`
- Cloudflare: SSL/TLS режим **Full (strict)**
- Регулярные обновления системы: `apt update && apt upgrade` (или эквивалент)

## 📚 Дополнительные ресурсы

- GitHub Environments: [https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- GitHub Secrets: [https://docs.github.com/en/actions/security-guides/encrypted-secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- Cloudflare Registrar: [https://developers.cloudflare.com/registrar/](https://developers.cloudflare.com/registrar/)
- DuckDNS Setup: [https://www.duckdns.org/install.jsp](https://www.duckdns.org/install.jsp)

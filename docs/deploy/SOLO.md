# 🚀 Solo Deployment Setup - PulsePlate

**Для соло-разработки:** Упрощённая, но безопасная конфигурация.

## 📋 Быстрая настройка

### 1. GitHub Environments (минимально необходимое)

**Создайте environments:**
- `staging` (для main branch)
- `production` (для tags v*)

**Secrets для `staging`:**
```bash
STAGING_DOMAIN=pulseplate-staging.duckdns.org
SSH_HOST_STAGING=ваш_ip_или_домен
SSH_USER=ubuntu
SSH_KEY=приватный_ssh_ключ
GHCR_READ_TOKEN=github_pat_token
```

**Secrets для `production`:**
```bash
PRODUCTION_DOMAIN=pulseplate.app
SSH_HOST_PRODUCTION=ваш_ip_или_домен
SSH_USER=ubuntu
SSH_KEY=тот_же_ssh_ключ (или отдельный)
GHCR_READ_TOKEN=тот_же_токен
```

### 2. Генерация SSH ключа (один раз)

```bash
# Генерация ключа (рекомендуется использовать passphrase для дополнительной безопасности)
ssh-keygen -t ed25519 -C "pulseplate-deploy" -f ~/.ssh/pulseplate_deploy
# При запросе passphrase: введите надёжный пароль (или нажмите Enter для ключа без пароля)
# ⚠️ Trade-off: ключ с passphrase безопаснее, но потребует настройки ssh-agent в CI/CD
```

**🔒 Безопасность:**

1. **Passphrase:** Используйте passphrase при генерации для защиты от компрометации приватного ключа. Если выбираете ключ без passphrase (для упрощения CI/CD), убедитесь, что ключ хранится только в GitHub Secrets и никогда не логируется.

2. **Проверка сервера:** Перед копированием публичного ключа **всегда проверяйте** hostname/IP и username сервера:

   ```bash
   # Проверьте fingerprint сервера при первом подключении
   ssh user@your-server
   ```

3. **Копирование публичного ключа:** Предпочтительные методы (по порядку безопасности):

   ```bash
   # Метод 1 (самый безопасный): ssh-copy-id
   ssh-copy-id -i ~/.ssh/pulseplate_deploy.pub user@your-server

   # Метод 2: явная команда с проверкой
   ssh user@your-server "mkdir -p ~/.ssh && chmod 700 ~/.ssh && \
     cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys" \
     < ~/.ssh/pulseplate_deploy.pub

   # Метод 3 (менее безопасный, но рабочий):
   # cat ~/.ssh/pulseplate_deploy.pub | ssh user@your-server \
   #   "mkdir -p ~/.ssh && chmod 700 ~/.ssh && \
   #    cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
   ```

4. **Права доступа:** Убедитесь, что директория и файлы имеют правильные права:

   ```bash
   # На локальной машине
   chmod 700 ~/.ssh
   chmod 600 ~/.ssh/pulseplate_deploy
   chmod 644 ~/.ssh/pulseplate_deploy.pub

   # На сервере (автоматически при использовании ssh-copy-id)
   # ~/.ssh: 700 (drwx------)
   # ~/.ssh/authorized_keys: 600 (-rw-------)
   ```

5. **⚠️ КРИТИЧЕСКИ ВАЖНО — Приватный ключ:**
   - **НИКОГДА** не коммитьте приватный ключ в Git
   - **НИКОГДА** не выводите приватный ключ в логи (`echo`, `print`, etc.)
   - **НИКОГДА** не отправляйте приватный ключ по email/мессенджерам

   **Безопасное добавление в GitHub Secrets:**

   **Через веб-интерфейс (рекомендуется):**

   1. GitHub → Settings → Secrets and variables → Actions → Environments → выберите environment
   2. New secret → Name: `SSH_KEY` → Value: вставьте содержимое приватного ключа
   3. Save

   **Через GitHub CLI (альтернатива):**

   ```bash
   # Установите GitHub CLI: https://cli.github.com/
   gh secret set SSH_KEY --env staging < ~/.ssh/pulseplate_deploy
   gh secret set SSH_KEY --env production < ~/.ssh/pulseplate_deploy
   ```

   **Проверка (безопасно, не показывает содержимое):**

   ```bash
   # НЕ используйте cat для просмотра перед копированием
   # Просто скопируйте напрямую в GitHub через веб или CLI
   ```

### 3. GitHub PAT Token

1. [https://github.com/settings/tokens](https://github.com/settings/tokens) → Generate new token (classic)
2. Отметьте только: `read:packages`
3. Скопируйте токен → добавьте как `GHCR_READ_TOKEN` в оба environment

## 🔒 Минимальная безопасность (для соло)

### Обязательно:

1. **SSH:** `PasswordAuthentication no` на сервере
2. **Cloudflare:** SSL Full (strict) + HSTS включён
3. **GitHub:** Branch protection на `main` (можно без reviewers, но с require status checks)
4. **Secrets:** Используйте GitHub Environments, не коммитьте в код
5. **Rate limiting на admin endpoints** — обязательно

### Опционально (но рекомендуется):

- Cloudflare WAF (базовые правила)
- Healthcheck после деплоя (автооткат при падении)

## ⚡ Упрощённый workflow

**Staging:** Автоматический деплой при push в `main`
**Production:** Автоматический деплой при создании tag `v*` (можно добавить manual approval, если нужно)

## 🎯 Быстрый старт

1. Регистрация доменов (см. `[DOMAIN.md](DOMAIN.md)`)
2. Добавьте секреты в GitHub (см. выше)
3. Push в main → staging деплой
4. Tag v1.0.0 → production деплой

**Готово!** 🎉

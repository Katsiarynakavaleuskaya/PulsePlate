# 🔐 Настройка GHCR_READ_TOKEN для CD-Test Workflow

**Проблема:** CD-Test workflow падает с ошибкой `denied: denied` при попытке pull из GHCR.

**Причина:** Токен `GHCR_READ_TOKEN` не настроен в GitHub Secrets или не имеет правильных permissions.

---

## ✅ Решение: Добавить токен в GitHub Secrets

### Шаг 1: Проверьте, что токен создан правильно

Ваш токен должен быть:
- **Тип:** Personal Access Token (Classic)
- **Scopes:** `read:packages` (обязательно!)
- **Формат:** Начинается с `ghp_...`

### Шаг 2: Добавьте токен в GitHub Secrets

**Важно:** Токен нужно добавить в **Environment Secrets**, а не в Repository Secrets!

#### Через веб-интерфейс (рекомендуется):

1. Откройте: https://github.com/Katsiarynakavaleuskaya/PulsePlate/settings/environments

2. **Если environment `staging` не существует:**
   - Нажмите **New environment**
   - Введите `staging`
   - Нажмите **Configure environment**
   - Нажмите **Save protection rules** (можно оставить пустым)

3. **Для environment `staging`:**
   - Нажмите на `staging`
   - В разделе **Environment secrets** нажмите **Add secret**
   - **Name:** `GHCR_READ_TOKEN`
   - **Value:** Вставьте ваш токен (начинается с `ghp_...`)
   - Нажмите **Add secret**

4. **Повторите для `production` (если нужно):**
   - Нажмите на `production` (или создайте новый)
   - Добавьте тот же секрет `GHCR_READ_TOKEN`

#### Через GitHub CLI (альтернатива):

```bash
# Установите GitHub CLI, если ещё не установлен
# macOS: brew install gh
# Linux: https://cli.github.com/

# Авторизуйтесь
gh auth login

# Добавьте секрет в staging environment
gh secret set GHCR_READ_TOKEN --env staging

# Введите токен, когда попросит (или передайте через stdin)
# echo "ghp_ваш_токен" | gh secret set GHCR_READ_TOKEN --env staging

# Повторите для production
gh secret set GHCR_READ_TOKEN --env production
```

---

## 🔍 Проверка настройки

### 1. Проверьте, что секрет добавлен:

1. GitHub → Settings → Environments → `staging`
2. В разделе **Environment secrets** должен быть `GHCR_READ_TOKEN` (показан как `●●●●●●●●`)

### 2. Проверьте permissions токена:

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Найдите ваш токен
3. Убедитесь, что scope `read:packages` отмечен

### 3. Проверьте, что workflow использует правильный environment:

В `.github/workflows/cd-test.yml` должно быть:

```yaml
jobs:
  validate-environment:
    runs-on: ubuntu-latest
    environment:
      name: staging  # ← Это важно!
```

---

## ⚠️ Частые ошибки

### Ошибка 1: Токен добавлен в Repository Secrets вместо Environment Secrets

**Симптом:** Workflow всё ещё падает с `denied: denied`

**Решение:**
- Удалите токен из Repository Secrets
- Добавьте в Environment Secrets (`staging` и `production`)

### Ошибка 2: Токен не имеет scope `read:packages`

**Симптом:** Workflow падает с `denied: denied`

**Решение:**
- Создайте новый токен с scope `read:packages`
- Обновите секрет в GitHub

### Ошибка 3: Environment не создан

**Симптом:** Workflow не может найти environment `staging`

**Решение:**
- Создайте environment `staging` в GitHub Settings → Environments

### Ошибка 4: Токен истёк

**Симптом:** Workflow падает с `denied: denied`

**Решение:**
- Создайте новый токен
- Обновите секрет в GitHub

---

## 🧪 Тестирование

После добавления токена:

1. **Запустите workflow вручную:**
   - GitHub → Actions → CD-Test
   - Нажмите **Run workflow** → выберите branch `main`

2. **Или сделайте push в main:**
   ```bash
   git commit --allow-empty -m "test: trigger CD-Test workflow"
   git push origin main
   ```

3. **Проверьте логи:**
   - GitHub → Actions → CD-Test → выберите последний run
   - В шаге "Test Docker image pull" должно быть:
     ```
     ✅ Docker login successful
     ✅ Docker image pull successful
     ```

---

## 📝 Текущий статус

**Фикс в коде:** ✅ Уже применён в main (PR #536)
- Используется `github.repository_owner` вместо `github.actor`
- Добавлена проверка наличия токена
- Добавлены сообщения об успехе

**Что осталось:** Добавить токен в GitHub Secrets

---

## 🔗 Полезные ссылки

- [GitHub Environments Documentation](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GHCR Authentication](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry#authenticating-to-the-container-registry)

---

**Last updated:** 2026-01-15

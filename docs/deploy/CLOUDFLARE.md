# 🔒 Cloudflare Security Setup - PulsePlate

## Быстрая настройка для Production домена

### 1. SSL/TLS настройки

1. Войдите в Cloudflare Dashboard: [https://dash.cloudflare.com](https://dash.cloudflare.com)
2. Выберите ваш домен `pulseplate.app`
3. **SSL/TLS** → **Overview**:
   - Режим: **Full (strict)** ✅
   - **Always Use HTTPS**: Включить ✅

4. **SSL/TLS** → **Edge Certificates** (или **Overview**):
   - **Minimum TLS Version**: Установить **TLS 1.3** ✅
   - **Automatic HTTPS Rewrites**: Включить ✅
   - **Opportunistic Encryption**: Включить ✅
   - Сохраните изменения

5. **Проверка TLS 1.3**:
   - Откройте `https://pulseplate.app` в браузере
   - Откройте DevTools (F12) → **Security** или **Network** → проверьте TLS версию
   - Или используйте SSL тест: [SSL Labs](https://www.ssllabs.com/ssltest/) или `openssl s_client -connect pulseplate.app:443 -tls1_3`
   - Убедитесь, что сайт обслуживается через TLS 1.3

### 2. HSTS (HTTP Strict Transport Security)

**SSL/TLS** → **Edge Certificates** → **HTTP Strict Transport Security (HSTS)**:

- ✅ Enable HSTS
- Max Age: **6 months** (минимум для начала)
- ✅ Include SubDomains
- ✅ Preload (опционально, требует времени)

### 3. WAF (Web Application Firewall)

**Security** → **WAF**:

- ✅ Enable WAF
- Выберите **Managed Rules**:
  - Cloudflare Managed Ruleset (базовые правила) ✅
  - Cloudflare OWASP Core Ruleset (опционально, может блокировать легитимные запросы)

### 4. Rate Limiting (для API protection)

**Security** → **WAF** → **Rate limiting rules** → **Create rule**:

#### Правило 1: Admin Endpoints Rate Limit

**Rule name:** `Admin API Rate Limit`
**Rule expression:**

```text
(http.request.uri.path starts_with "/api/v1/admin/" and http.request.method == "POST" and http.host eq "pulseplate.app")
```

**Threshold:**

- Requests: `30` (начальное значение для admin операций)
- Period: `1 minute`

**Action:** Block

**IP Whitelisting (опционально):**

- Добавьте условие для исключения известных admin IP:

  ```text
  and not (ip.src in {YOUR_ADMIN_IP_1 YOUR_ADMIN_IP_2})
  ```

- Или создайте IP List в **Manage Account** → **Configurations** → **Lists** для управления whitelist

**Сохранить.**

#### Правило 2: Premium Endpoints Rate Limit

**Rule name:** `Premium API Rate Limit`
**Rule expression:**

```text
(http.request.uri.path starts_with "/api/v1/premium/" and http.request.method == "POST" and http.host eq "pulseplate.app")
```

**Threshold:**

- Requests: `20` (начальное значение для premium пользователей)
- Period: `1 minute`

**Action:** Block

**Сохранить.**

**📊 Мониторинг и итеративная настройка rate-limit:**

После настройки правил критически важно отслеживать их работу и корректировать пороги на основе реального трафика:

1. **Начальная настройка:**
   - **Рекомендуется начать с более высоких порогов** (20-30 запросов/мин), чтобы избежать блокировки легитимных пользователей
   - После сбора данных о реальном трафике (1-2 недели) постепенно ужесточайте лимиты

2. **Проверка блокировок и false positives:**
   - Перейдите в **Analytics & Logs** → **Security Events**
   - Фильтруйте по каждому rate-limit правилу отдельно
   - **Обязательно проверяйте логи на false positives** (легитимные запросы, которые были заблокированы)
   - Отслеживайте паттерны блокировок по времени суток и типам операций

3. **Независимая корректировка порогов:**
   - **Admin endpoints:** могут требовать более высоких лимитов (массовые операции, импорт данных)
     - Типичный диапазон: 30-50 запросов/мин для admin операций
   - **Premium endpoints:** обычно требуют умеренных лимитов
     - Типичный диапазон: 20-30 запросов/мин для premium функций
   - Корректируйте каждое правило независимо на основе его использования

4. **IP Whitelisting для администраторов:**
   - Создайте IP List для известных admin IP адресов или диапазонов
   - Исключите эти IP из rate limiting для критически важных операций
   - Регулярно обновляйте список при изменении admin IP

5. **Итеративный процесс настройки:**
   - **Неделя 1-2:** Мониторинг с высокими порогами (30+ req/min)
   - **Неделя 3-4:** Анализ логов, выявление паттернов, первая корректировка
   - **Месяц 2:** Постепенное ужесточение на основе собранных данных
   - **Далее:** Ежемесячный review логов и корректировка при необходимости

6. **Рекомендации по мониторингу:**
   - Настройте алерты на превышение порога блокировок (например, >10 блокировок за час)
   - Ведите документацию изменений порогов и причин корректировки
   - Анализируйте корреляцию между блокировками и жалобами пользователей
   - Рассмотрите использование **Log Push** для экспорта логов в внешнюю систему анализа

### 5. Bot Fight Mode

**Security** → **Bots**:

- **Bot Fight Mode**: ON (soft mode, не блокирует полностью)
- Это защитит от простых ботов без блокировки реальных пользователей

### 6. DNS настройки

**DNS** → **Records**:

- Добавьте A-запись: `@` → `your-server-ip` → **Proxied** (оранжевое облако) ✅
- Предпочтительно добавьте `CNAME`: `www` → `pulseplate.app` → **Proxied** ✅
  Если CNAME недоступен в вашей схеме, используйте отдельную A-запись `www` → `your-server-ip`.
- Удалите конфликтующие apex `AAAA` записи, если production root остаётся на текущем repo-backed runtime.
- Не подключайте `pulseplate.app` или `www.pulseplate.app` к Figma Sites, пока live app/API обслуживаются текущим production stack.

**Важно:** Проксирование (Proxied) включает DDoS защиту и кеширование.

**Важно для Figma custom domains:** если нужен Figma-hosted preview, вынесите его на отдельный preview subdomain. Не смешивайте root-domain ownership между Cloudflare/Caddy production и Figma Sites.

### 6a. Канонический порядок remediation для `www -> 525`

Если `https://pulseplate.app` открывается, а `https://www.pulseplate.app` возвращает `525`, действуйте только в этом порядке:

1. Из репозитория запустите `python3 scripts/check_domain_tls.py --domain pulseplate.app`.
   - При включённом Cloudflare proxy diagnostic может показывать `www CNAME: (none)`; это не drift само по себе, если `www` всё ещё резолвится через `A` и отдаёт healthy redirect на apex.
2. Если diagnostic подтверждает `www 525`, проверьте DNS ownership:
   - `@` остаётся repo-owned production root
   - `www` остаётся **Proxied** repo-owned record (`CNAME www -> pulseplate.app` предпочтительно)
   - `www` не должен указывать на Figma Sites
3. Проверьте SSL/TLS mode в Cloudflare: только **Full (strict)**.
4. На origin выполните `bash scripts/diagnose_production.sh`, чтобы проверить Caddy, контейнеры и origin-конфигурацию для apex + `www`.
5. Только после live-подтверждения healthy redirect обновляйте evidence в repo и закрывайте remediation PR.

**Запрещено:** маскировать `525` через `Flexible` или другой downgrade SSL mode.
**Запрещено:** подключать `pulseplate.app` или `www.pulseplate.app` к Figma Sites, пока live app/API обслуживаются текущим production stack.

### 7. API Tokens (для автоматизации)

**My Profile** → **API Tokens** → **Create Token**:

- **Template:** DNS Edit (zone-specific)
- **Zone Resources:**
  - Include: Specific zone
  - Zone: `pulseplate.app`
- **Permissions:**
  - DNS → Zone → Read
  - DNS → Zone DNS → Edit
- **TTL:** 1 year (или меньше)

**Используйте этот токен** для любых автоматизированных DNS операций.

## ✅ Минимальный чеклист

- [ ] SSL/TLS режим: **Full (strict)**
- [ ] HSTS включён (6+ months)
- [ ] Always Use HTTPS включён
- [ ] WAF включён (базовые Managed Rules)
- [ ] Rate limiting на admin endpoints (10 req/min)
- [ ] Bot Fight Mode включён (soft)
- [ ] DNS записи с **Proxied** (оранжевое облако)
- [ ] Нет конфликтующего apex `AAAA` record для active production ownership
- [ ] `python3 scripts/check_domain_tls.py --domain pulseplate.app` показывает healthy apex + `www -> apex` redirect
- [ ] API Token создан (scope: только DNS для вашей зоны)

## 🔍 Проверка

После настройки проверьте:

### ⚠️ Важные замечания по тестированию rate limiting

1. **Аутентификация обязательна**: Защищенные эндпоинты требуют валидные токены/API ключи
2. **Валидное тело запроса**: Запросы должны содержать корректные данные для прохождения валидации
3. **Тестовые эндпоинты**: Рекомендуется создать специальный `/api/v1/test/rate-limit` эндпоинт без аутентификации для тестирования
4. **Мониторинг заголовков**: Проверяйте заголовки `X-RateLimit-*` в ответах для отладки

```bash
# SSL сертификат
curl -I https://pulseplate.app/health

# HSTS заголовок
curl -I https://pulseplate.app/health | grep -i strict-transport

# Rate limit тестирование с аутентификацией
# Вариант 1: Используйте тестовый API ключ из переменной окружения
export TEST_API_KEY="your-test-api-key-here"  # pragma: allowlist secret  # Замените на реальный ключ

# Тест с валидным телом запроса и аутентификацией
for i in {1..15}; do \
  echo "Request $i: "; \
  curl -s -o /dev/null -w "HTTP %{http_code} - Time: %{time_total}s\n" \
    -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${TEST_API_KEY}" \
    -d '{"action": "get_status", "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' \
    https://pulseplate.app/api/v1/admin/status; \
  sleep 0.1; \
done

# Вариант 2: Используйте публичный эндпоинт для тестирования rate limiting
# (например, эндпоинт калькулятора BMI с валидными данными)
for i in {1..15}; do \
  echo "Request $i: "; \
  curl -s -o /dev/null -w "HTTP %{http_code}\n" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"weight": 70, "height": 175, "age": 30, "sex": "male"}' \
    https://pulseplate.app/api/v1/bmi/calculate; \
done

# Проверка заголовков rate limit в ответе
curl -I -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TEST_API_KEY}" \
  -d '{"action": "get_status"}' \
  https://pulseplate.app/api/v1/admin/status | grep -i "x-ratelimit"
```

### 🧪 Создание тестового эндпоинта для rate limiting

Для упрощения тестирования добавьте в FastAPI приложение:

```python
# app/routers/test.py (только для staging/development)
from fastapi import APIRouter, Response
from datetime import datetime

router = APIRouter(prefix="/api/v1/test", tags=["test"])

@router.post("/rate-limit")
async def test_rate_limit(response: Response):
    """Тестовый эндпоинт для проверки rate limiting без аутентификации."""
    response.headers["X-Test-Timestamp"] = datetime.utcnow().isoformat()
    return {"status": "ok", "message": "Rate limit test endpoint"}

# В app.py добавьте условно:
if settings.ENVIRONMENT in ["staging", "development"]:
    from app.routers import test
    app.include_router(test.router)
```

Тестирование с этим эндпоинтом:

```bash
# Простой тест без аутентификации
for i in {1..15}; do \
  echo "Request $i: $(curl -s -w ' - HTTP %{http_code}' \
    -X POST https://pulseplate.app/api/v1/test/rate-limit)"; \
done
```

## ⚠️ Важно для соло-разработки

- Все настройки можно сделать вручную в Dashboard — не нужны сложные скрипты
- WAF может блокировать легитимные запросы — начните с минимальных правил
- Rate limiting на admin endpoints защитит от брутфорса
- Cloudflare кеширует статику автоматически — это ускорит загрузку

## 📚 Дополнительные ресурсы

- Cloudflare Dashboard: [https://dash.cloudflare.com](https://dash.cloudflare.com)
- Cloudflare SSL Docs: [https://developers.cloudflare.com/ssl/](https://developers.cloudflare.com/ssl/)
- Cloudflare WAF Docs: [https://developers.cloudflare.com/waf/](https://developers.cloudflare.com/waf/)

# 🔒 Cloudflare Security Setup - PulsePlate

## Быстрая настройка для Production домена

### 1. SSL/TLS настройки

1. Войдите в Cloudflare Dashboard: https://dash.cloudflare.com
2. Выберите ваш домен `pulseplate.app`
3. **SSL/TLS** → **Overview**:
   - Режим: **Full (strict)** ✅
   - **Always Use HTTPS**: Включить ✅
   - **Minimum TLS Version**: TLS 1.2 (по умолчанию)

4. **SSL/TLS** → **Edge Certificates**:
   - **Automatic HTTPS Rewrites**: Включить ✅
   - **Opportunistic Encryption**: Включить ✅

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

**Rule name:** `API Rate Limit`
**Rule expression:**
```text
(http.request.uri.path contains "/api/v1/admin/" or http.request.uri.path contains "/api/v1/premium/")
```

**Threshold:**
- Requests: `10`
- Period: `1 minute`

**Action:** Block

**Сохранить.**

### 5. Bot Fight Mode

**Security** → **Bots**:
- **Bot Fight Mode**: ON (soft mode, не блокирует полностью)
- Это защитит от простых ботов без блокировки реальных пользователей

### 6. DNS настройки

**DNS** → **Records**:
- Добавьте A-запись: `@` → `your-server-ip` → **Proxied** (оранжевое облако) ✅
- Добавьте A-запись: `www` → `your-server-ip` → **Proxied** ✅

**Важно:** Проксирование (Proxied) включает DDoS защиту и кеширование.

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
- [ ] API Token создан (scope: только DNS для вашей зоны)

## 🔍 Проверка

После настройки проверьте:

```bash
# SSL сертификат
curl -I https://pulseplate.app/health

# HSTS заголовок
curl -I https://pulseplate.app/health | grep -i strict-transport

# Rate limit (должен блокировать после 10 запросов)
for i in {1..15}; do curl -s -o /dev/null -w "%{http_code}\n" https://pulseplate.app/api/v1/admin/status; done
```

## ⚠️ Важно для соло-разработки

- Все настройки можно сделать вручную в Dashboard — не нужны сложные скрипты
- WAF может блокировать легитимные запросы — начните с минимальных правил
- Rate limiting на admin endpoints защитит от брутфорса
- Cloudflare кеширует статику автоматически — это ускорит загрузку

## 📚 Дополнительные ресурсы

- Cloudflare Dashboard: https://dash.cloudflare.com
- Cloudflare SSL Docs: https://developers.cloudflare.com/ssl/
- Cloudflare WAF Docs: https://developers.cloudflare.com/waf/

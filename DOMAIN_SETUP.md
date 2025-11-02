# 🌐 Domain Setup Guide - PulsePlate

## Рекомендуемые варианты доменов

### 🆓 Бесплатные варианты (для MVP/Staging)

#### Option 1: DuckDNS (Рекомендуется для Staging)

- **URL**: `pulseplate-staging.duckdns.org`
- **Плюсы**:
  - Полностью бесплатно
  - Стабильный сервис
  - Легко настраивается
  - Подходит для тестирования
- **Настройка**: <https://www.duckdns.org>
- **Стоимость**: $0/год

#### Option 2: Freenom (для тестов)

- **URL**: `pulseplate-staging.tk` или `pulseplate-staging.ml`
- **Плюсы**: Настоящий домен, бесплатно
- **Минусы**: Могут отзывать домены, не рекомендуется для production
- **Стоимость**: $0/год

### 💰 Бюджетные варианты (для Production)

#### Option 1: Cloudflare Registrar + .xyz (Лучший выбор)

- **URL**: `pulseplate.xyz`
- **Плюсы**:
  - Всего $1.03/год
  - Бесплатный SSL (автоматически)
  - Бесплатный DNS с DDoS защитой
  - Быстрая настройка
  - Надёжный регистратор
- **Стоимость**: $1.03/год (~₽100/год)
- **Где купить**: <https://www.cloudflare.com/products/registrar/>

#### Option 2: Cloudflare Registrar + .app

- **URL**: `pulseplate.app`
- **Плюсы**:
  - Премиум-вид для health-приложений
  - HSTS включён по умолчанию
  - Бесплатный SSL + DNS
- **Стоимость**: ~$7/год (~₽700/год)
- **Где купить**: <https://www.cloudflare.com/products/registrar/>

#### Option 3: Namecheap .xyz

- **URL**: `pulseplate.xyz`
- **Плюсы**: Дешево, часто промо-акции
- **Стоимость**: $1-2/год
- **Где купить**: <https://www.namecheap.com>

## 📋 Конфигурация для GitHub Environments

### Staging Environment

**Secrets для `staging` environment:**

```bash
STAGING_DOMAIN=pulseplate-staging.duckdns.org
# Или если используете Freenom:
# STAGING_DOMAIN=staging-pulseplate.tk
```

### Production Environment

**Secrets для `production` environment:**

```bash
PRODUCTION_DOMAIN=pulseplate.xyz
# Или если используете .app:
# PRODUCTION_DOMAIN=pulseplate.app
```

## 🔧 Настройка DNS

### DuckDNS (Staging)

1. Зарегистрируйтесь на <https://www.duckdns.org>
2. Создайте поддомен: `pulseplate-staging`
3. Добавьте A-запись в DuckDNS с IP вашего сервера
4. Проверьте: `curl https://pulseplate-staging.duckdns.org/health`

### Cloudflare (Production)

1. Купите домен через Cloudflare Registrar
2. Добавьте A-запись: `@` → `your-server-ip`
3. Добавьте A-запись для www (опционально): `www` → `your-server-ip`
4. SSL/TLS режим: Full (automatic)
5. Проверьте: `curl https://pulseplate.xyz/health`

## 🚀 Быстрый старт

### Минимальный вариант (бесплатно)

```yaml
# .github/workflows/cd.yml уже настроен на использование secrets
STAGING_DOMAIN: pulseplate-staging.duckdns.org
PRODUCTION_DOMAIN: pulseplate-staging.duckdns.org  # Можно использовать тот же для тестов
```

### Production-ready вариант

```yaml
STAGING_DOMAIN: pulseplate-staging.duckdns.org
PRODUCTION_DOMAIN: pulseplate.xyz  # $1/год через Cloudflare
```

## 📝 Примечания

- **Staging** можно оставить на DuckDNS бесплатно навсегда
- **Production** лучше использовать платный домен ($1/год — минимальные затраты)
- Cloudflare Registrar включает бесплатный SSL, что экономит на сертификатах
- Для health-приложений `.app` домен выглядит профессиональнее, но `.xyz` дешевле

## 🔒 SSL Сертификаты

Все варианты поддерживают бесплатный SSL:

- **DuckDNS**: Автоматический через Let's Encrypt (настроится Caddy)
- **Cloudflare**: Автоматический SSL в режиме Full
- **Freenom**: Настройка Let's Encrypt через Caddy

## ⚡ Рекомендация финальная

**Текущий выбор (согласно вашему решению):**

- **Staging**: `pulseplate-staging.duckdns.org` (бесплатно) ✅
- **Production**: `pulseplate.app` (~$7/год, Cloudflare) ✅

**🔗 Ссылки для регистрации:**

- **Cloudflare Registrar** (Production домен): <https://dash.cloudflare.com/registrar/search>
- **DuckDNS** (Staging поддомен): <https://www.duckdns.org> (войти через GitHub)

**📖 Подробная инструкция по секретам:** См. файл `GITHUB_SECRETS_SETUP.md`

## 🚀 TON Cloud / Новая платформа Павла Дурова

Павел Дуров анонсировал развитие инфраструктуры TON для децентрализованных приложений и развертывания программ.

**🔗 Полезные ссылки:**

- **TON Blockchain**: <https://ton.org>
- **TON Developer Docs**: <https://docs.ton.org>
- **TON Cloud** (если доступен): <https://cloud.ton.org>
- **TON Developer Portal**: <https://tondev.io>

**📝 Примечание:** Для веб-приложений (FastAPI) эта платформа может стать доступной позже. Следите за обновлениями на официальных каналах TON. Возможно, в будущем будет возможность деплоя на децентрализованную инфраструктуру TON, что может быть более экономичным решением.

## 📋 Следующие шаги

1. ✅ Зарегистрируйтесь на Cloudflare и купите домен `pulseplate.app`
2. ✅ Зарегистрируйтесь на DuckDNS и создайте поддомен `pulseplate-staging`
3. ✅ Добавьте секреты в GitHub Environments (см. `GITHUB_SECRETS_SETUP.md`)
4. ✅ Настройте DNS записи на обоих сервисах
5. ✅ После настройки разкомментируйте SSH deployment шаги в `.github/workflows/cd.yml`

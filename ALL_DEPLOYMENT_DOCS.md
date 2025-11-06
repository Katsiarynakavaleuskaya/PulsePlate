# 📋 Полный список всех документов по деплою

**Версия:** 2025-11-02
**Статус:** Актуально
**Last-verified of links:** 2025-11-02

> ⚠️ **Важно для maintainers:** При изменении любого целевого документа (например, `DEPLOYMENT_FULL_GUIDE.md`, `DOMAIN_SETUP.md` и т.д.) необходимо обновить соответствующий тег `(last-verified: YYYY-MM-DD)` в этом файле для всех ссылок на этот документ.

---

## 🎯 С чего начать (для новичков)

### ⭐ **НАЧНИТЕ ОТСЮДА:**

1. **`DEPLOYMENT_FULL_GUIDE.md`** (last-verified: 2025-11-02) — главная инструкция
   - Полная пошаговая инструкция от начала до конца
   - Время: 2-3 часа выполнения

2. **`DEPLOYMENT_READING_LIST.md`** (last-verified: 2025-11-02) — навигатор по документам
   - Какой документ читать и когда
   - Рекомендуемый порядок чтения

---

## 📚 Все документы (по категориям)

### 🔰 Главные документы

| Файл | Описание | Когда читать |
|------|----------|--------------|
| `DEPLOYMENT_FULL_GUIDE.md` (last-verified: 2025-11-02) | ⭐ Главная инструкция для новичков | **ПЕРВЫМ** |
| `DEPLOYMENT_READING_LIST.md` (last-verified: 2025-11-02) | Навигатор: какие документы читать | Перед началом |
| `ALL_DEPLOYMENT_DOCS.md` (last-verified: 2025-11-02) | Этот файл — полный список | Справочно |

### 🌐 Домены и DNS

| Файл | Описание | Когда читать |
|------|----------|--------------|
| `DOMAIN_SETUP.md` (last-verified: 2025-11-02) | Выбор и регистрация доменов (Cloudflare, DuckDNS) | Перед регистрацией |
| `CLOUDFLARE_SECURITY_SETUP.md` (last-verified: 2025-11-02) | Настройка безопасности Cloudflare (SSL, HSTS, WAF) | После регистрации домена |

### 💻 Серверы и окружения

| Файл | Описание | Когда читать |
|------|----------|--------------|
| `STAGING_SETUP.md` (last-verified: 2025-11-02) | Детальная настройка staging сервера | При настройке staging |
| `PRODUCTION_SETUP.md` (last-verified: 2025-11-02) | Детальная настройка production сервера + security hardening | При настройке production |
| `SOLO_DEPLOYMENT_SETUP.md` (last-verified: 2025-11-02) | Упрощённая версия для соло-разработчика | Для быстрого обзора |

### 🔐 GitHub и секреты

| Файл | Описание | Когда читать |
|------|----------|--------------|
| `GITHUB_SECRETS_SETUP.md` (last-verified: 2025-11-02) | Подробная настройка GitHub Environments и секретов | Перед добавлением секретов |

### ⚙️ CI/CD и автоматизация

| Файл | Описание | Когда читать |
|------|----------|--------------|
| `CI_SETUP.md` (last-verified: 2025-11-02) | Как работает CI (Continuous Integration) | Когда CI падает или для понимания |
| `.github/workflows/cd.yml` (last-verified: 2025-11-02) | CD workflow (автоматический деплой) | Справочно (уже настроен) |

### 📦 Дополнительно (опционально)

| Файл | Описание | Когда читать |
|------|----------|--------------|
| `CRON_SETUP.md` (last-verified: 2025-11-02) | Настройка периодических задач (cron) | Когда нужны автоматические задачи |
| `TON_RFC.md` (last-verified: 2025-11-02) | Исследование TON платформы (R&D) | Если интересуетесь TON |

---

## 🗺️ Быстрый маршрут

### Для первого деплоя:

```text
1. DEPLOYMENT_FULL_GUIDE.md (last-verified: 2025-11-02) (главная инструкция)
   ↓
2. DOMAIN_SETUP.md (last-verified: 2025-11-02) (регистрация доменов)
   ↓
3. CLOUDFLARE_SECURITY_SETUP.md (last-verified: 2025-11-02) (безопасность)
   ↓
4. STAGING_SETUP.md (last-verified: 2025-11-02) или PRODUCTION_SETUP.md (last-verified: 2025-11-02) (настройка сервера)
   ↓
5. GITHUB_SECRETS_SETUP.md (last-verified: 2025-11-02) (добавление секретов)
   ↓
6. Первый деплой!
```

### Для быстрого старта (опытные):

```text
1. SOLO_DEPLOYMENT_SETUP.md (last-verified: 2025-11-02) (обзор)
   ↓
2. GITHUB_SECRETS_SETUP.md (last-verified: 2025-11-02) (секреты)
   ↓
3. Деплой
```

---

## 📂 Структура файлов в репозитории

```
BMI-App_2025_clean/
├── DEPLOYMENT_FULL_GUIDE.md (last-verified: 2025-11-02)          ⭐ Главная инструкция
├── DEPLOYMENT_READING_LIST.md (last-verified: 2025-11-02)         Навигатор
├── ALL_DEPLOYMENT_DOCS.md (last-verified: 2025-11-02)             Этот файл
│
├── DOMAIN_SETUP.md (last-verified: 2025-11-02)                    Домены
├── CLOUDFLARE_SECURITY_SETUP.md (last-verified: 2025-11-02)       Cloudflare
│
├── STAGING_SETUP.md (last-verified: 2025-11-02)                   Staging сервер
├── PRODUCTION_SETUP.md (last-verified: 2025-11-02)                Production сервер
├── SOLO_DEPLOYMENT_SETUP.md (last-verified: 2025-11-02)           Соло-версия
│
├── GITHUB_SECRETS_SETUP.md (last-verified: 2025-11-02)            GitHub секреты
│
├── CI_SETUP.md (last-verified: 2025-11-02)                        CI документация
│
├── CRON_SETUP.md (last-verified: 2025-11-02)                      Cron (опционально)
└── TON_RFC.md (last-verified: 2025-11-02)                         TON (R&D)
```

---

## ✅ Чеклист перед деплоем

После прочтения документов проверьте:

- [ ] Знаю, какой домен для staging (DuckDNS)
- [ ] Знаю, какой домен для production (Cloudflare)
- [ ] Зарегистрировал домены
- [ ] Настроил DNS записи
- [ ] Настроил Cloudflare безопасность
- [ ] Настроил сервер (Docker, безопасность)
- [ ] Создал SSH ключи
- [ ] Создал GitHub токены
- [ ] Добавил секреты в GitHub Environments
- [ ] Знаю, как запустить первый деплой

---

## 🔍 Поиск по проблемам

### Проблема с доменами?
→ `DOMAIN_SETUP.md` (last-verified: 2025-11-02) → раздел "Частые проблемы"

### Проблема с Cloudflare?
→ `CLOUDFLARE_SECURITY_SETUP.md` (last-verified: 2025-11-02)

### Проблема с сервером?
→ `STAGING_SETUP.md` (last-verified: 2025-11-02) или `PRODUCTION_SETUP.md` (last-verified: 2025-11-02)

### Проблема с GitHub Secrets?
→ `GITHUB_SECRETS_SETUP.md` (last-verified: 2025-11-02)

### Проблема с деплоем?
→ `DEPLOYMENT_FULL_GUIDE.md` (last-verified: 2025-11-02) → раздел "Частые проблемы"

### CI/CD не работает?
→ `CI_SETUP.md` (last-verified: 2025-11-02) или проверьте `.github/workflows/cd.yml` (last-verified: 2025-11-02)

---

## 📞 Получить помощь

1. Перечитайте соответствующий раздел в **`DEPLOYMENT_FULL_GUIDE.md`** (last-verified: 2025-11-02)
2. Проверьте раздел "Частые проблемы" в нужном документе
3. Посмотрите логи GitHub Actions
4. Проверьте логи на сервере: `docker logs <container_name>`

---

## 🎓 Для новичков

**Рекомендации:**

1. ✅ Читайте **строго по порядку** из `DEPLOYMENT_READING_LIST.md` (last-verified: 2025-11-02)
2. ✅ Выполняйте шаги **последовательно**, не пропускайте
3. ✅ Делайте **скриншоты** важных настроек
4. ✅ Сохраняйте **пароли и ключи** в безопасном месте
5. ✅ Не бойтесь **ошибок** — они нормальны, есть решения

---

**Последнее обновление:** 2025-11-02
**Версия документации:** 1.0

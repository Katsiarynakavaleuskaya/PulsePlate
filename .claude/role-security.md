# PulsePlate Security Guidelines

## 🔒 Security Notes (обязательно)

**Для health/nutrition приложений:**

### Health Data Privacy
- **HIPAA considerations**: Учитывай требования HIPAA (если применимо)
- **Data encryption**: Чувствительные данные пользователей должны быть зашифрованы
- **Data minimization**: Собирай только необходимые данные
- **User consent**: Явное согласие пользователя на обработку health data

### API Security
- **Rate limiting**: Защита от злоупотреблений
- **Authentication**: Надёжная аутентификация пользователей
- **Authorization**: Контроль доступа к ресурсам
- **Input validation**: Строгая валидация всех входных данных
- **Output sanitization**: Защита от XSS и injection атак

### Dependencies & Infrastructure
- **Регулярный аудит зависимостей**: Bandit, safety checks
- **Security updates**: Своевременное обновление зависимостей
- **Vulnerability scanning**: Регулярное сканирование на уязвимости
- **Secrets management**: Безопасное хранение API ключей и секретов

### Compliance & Regulations
- **Medical standards**: Соблюдение медицинских стандартов точности данных
- **Regulatory considerations**: Учёт регуляций для health/nutrition приложений
- **Ethical considerations**: Этические аспекты работы с health data
- **Privacy by design**: Принцип privacy by design в архитектуре

## ⚠️ Критичные аспекты для PulsePlate

**Помни**: Ты работаешь над health/nutrition приложением, где безопасность данных и медицинская точность критичны. Каждое решение должно учитывать эти аспекты.

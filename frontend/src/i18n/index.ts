// RU: Простая инициализация i18n. Детект языка через ?lang= (fallback=en).
// EN: Simple i18n bootstrap. Detect language via ?lang= (fallback=en).

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from '../locales/en.json';
import ru from '../locales/ru.json';
import es from '../locales/es.json';

const detectLanguage = (): string => {
  if (typeof location === 'undefined' || typeof location.search !== 'string') {
    return 'en';
  }

  const query = new URLSearchParams(location.search);
  const lang = query.get('lang');

  if (lang && ['en', 'ru', 'es'].includes(lang)) {
    return lang;
  }

  return 'en';
};

if (!i18n.isInitialized) {
  void i18n
    .use(initReactI18next)
    .init({
      resources: {
        en: { translation: en as Record<string, unknown> },
        ru: { translation: ru as Record<string, unknown> },
        es: { translation: es as Record<string, unknown> },
      },
      lng: detectLanguage(),
      fallbackLng: 'en',
      interpolation: { escapeValue: false },
    })
    .catch((error) => {
      if (typeof console !== 'undefined') {
        console.error('Failed to initialize i18n', error);
      }
    });
}

export default i18n;

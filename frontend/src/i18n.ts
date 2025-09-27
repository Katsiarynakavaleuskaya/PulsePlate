import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import ru from "./locales/ru.json";
import es from "./locales/es.json";

// Minimal i18n bootstrap for tests and app runtime
void i18n
  .use(initReactI18next)
  .init({
    lng: "en",
    fallbackLng: "en",
    resources: {
      en: { translation: en as unknown as Record<string, unknown> },
      ru: { translation: ru as unknown as Record<string, unknown> },
      es: { translation: es as unknown as Record<string, unknown> },
    },
    interpolation: { escapeValue: false },
  });

export default i18n;

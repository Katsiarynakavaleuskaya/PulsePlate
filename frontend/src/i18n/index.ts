// RU: Простая инициализация i18n. Детект языка через ?lang= (fallback=en).
// EN: Simple i18n bootstrap. Detect language via ?lang= (fallback=en).

import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "../locales/en.json";
import ru from "../locales/ru.json";
import es from "../locales/es.json";

const urlLang = new URLSearchParams(location.search).get("lang") ?? "en";

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, ru: { translation: ru }, es: { translation: es } },
  lng: urlLang,
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export default i18n;

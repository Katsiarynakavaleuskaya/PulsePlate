// RU: Неблокирующая проверка i18n — логируем 'common.ok' на старте.
// EN: Non-blocking i18n smoke — log 'common.ok' on startup.

import { log, logError } from "../lib/analytics";
import i18n from "./index";

export function i18nSmoke(): void {
  try {
    // Always test translation functionality, regardless of initialization status
    const translatedOk = i18n.t("common.ok", { defaultValue: "OK" });

    // Check if translation actually worked (not just returned the default)
    const isTranslationWorking = translatedOk !== "OK" || i18n.language === "en";

    // Verify i18n is properly initialized AND translations are working
    const isFullyWorking = i18n.isInitialized && isTranslationWorking;

    log("i18n_ok", {
      value: isFullyWorking,
      translation: translatedOk,
      isInitialized: i18n.isInitialized,
      language: i18n.language,
      isTranslationWorking
    });
  } catch (error) {
    logError(error);
    log("i18n_ok", { value: false, error: error instanceof Error ? error.message : String(error) });
  }
}

// RU: Неблокирующая проверка i18n — логируем 'common.ok' на старте.
// EN: Non-blocking i18n smoke — log 'common.ok' on startup.

import { log, logError } from "../lib/analytics";
import i18n from "./index";

/**
 * Performs a non-blocking smoke test of i18n functionality.
 * Tests translation capabilities and logs comprehensive diagnostics.
 *
 * This function:
 * - Always tests translation functionality regardless of initialization status
 * - Detects broken translation resources
 * - Provides detailed logging for debugging i18n issues
 * - Handles errors gracefully
 */
export function i18nSmoke(): void {
  try {
    // Test translation functionality without default value to detect missing resources
    const translatedOk = i18n.t("common.ok");

    // Check if translation actually worked by verifying:
    // 1. i18n is initialized
    // 2. Resource bundle exists for the active language
    // 3. Translation returned a valid string (not the key itself)
    // 4. Translation is not empty
    const { isInitialized, language } = i18n;
    const hasResourceBundle = i18n.hasResourceBundle(language, "translation");
    const hasValidTranslation = translatedOk &&
                               translatedOk !== "common.ok" &&
                               translatedOk.trim().length > 0;

    // Verify i18n is properly initialized AND resource bundle exists AND translations are working
    const isFullyWorking = isInitialized && hasResourceBundle && hasValidTranslation;

    log("i18n_ok", {
      value: isFullyWorking,
      translation: translatedOk,
      isInitialized,
      language,
      hasResourceBundle,
      hasValidTranslation,
      // Additional diagnostics for debugging
      resourceKeys: i18n.getResourceBundle(language, "translation") ?
        Object.keys(i18n.getResourceBundle(language, "translation")) : []
    });
  } catch (error) {
    logError(error);
    const { isInitialized, language } = i18n;
    log("i18n_ok", {
      value: false,
      error: error instanceof Error ? error.message : String(error),
      isInitialized,
      language
    });
  }
}

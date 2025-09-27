// RU: Неблокирующая проверка i18n — логируем 'common.ok' на старте.
// EN: Non-blocking i18n smoke — log 'common.ok' on startup.
import i18n from "./index";

export function i18nSmoke(): void {
  try {
    // Дождёмся инициализации, но не тормозим UI:
    setTimeout(() => {
      const ok = i18n.t("common.ok");
      // eslint-disable-next-line no-console
      console.log(`[i18n] OK => ${ok}`);
    }, 0);
  } catch {
    // eslint-disable-next-line no-console
    console.warn("[i18n] smoke failed");
  }
}

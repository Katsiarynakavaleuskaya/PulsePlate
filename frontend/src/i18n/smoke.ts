// RU: Неблокирующая проверка i18n — логируем 'common.ok' на старте.
// EN: Non-blocking i18n smoke — log 'common.ok' on startup.
import i18n from "./index";

export function i18nSmoke(): void {
  const logOk = () => {
    try {
      const ok = i18n.t("common.ok");
      // eslint-disable-next-line no-console
      console.log(`[i18n] OK => ${ok}`);
    } catch {
      // eslint-disable-next-line no-console
      console.warn("[i18n] smoke failed");
    }
  };

  if (i18n.isInitialized) {
    logOk();
    return;
  }

  const handler = () => {
    logOk();
    i18n.off("initialized", handler);
  };

  i18n.on("initialized", handler);
}

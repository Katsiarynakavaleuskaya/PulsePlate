// RU: Неблокирующая проверка i18n — логируем 'common.ok' на старте.
// EN: Non-blocking i18n smoke — log 'common.ok' on startup.
import i18n from "./index";
import { log, logError } from "../lib/analytics";

export function i18nSmoke(): void {
  const logOk = () => {
    try {
      const ok = i18n.t("common.ok");
      log("i18n_ok", { value: ok });
    } catch (error) {
      logError(error);
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

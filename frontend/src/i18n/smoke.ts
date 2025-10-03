import { log, logError } from "../lib/analytics";
import i18n from "./index";

export function i18nSmoke(): void {
  const ok = i18n.isInitialized;
  try {
    log("i18n_ok", { value: ok });
  } catch (error) {
    logError(error);
  }
}

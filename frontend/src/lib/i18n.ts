export function getClientLocale(defaultLocale: string = "en"): string {
  const docLang =
    typeof document !== "undefined" && document.documentElement?.lang
      ? document.documentElement.lang
      : "";
  const navLang =
    typeof navigator !== "undefined" && typeof navigator.language === "string"
      ? navigator.language
      : "";
  const raw = docLang || navLang || "";
  const normalized = raw ? raw.split("-")[0]?.toLowerCase() : "";
  return normalized && normalized.length === 2 ? normalized : defaultLocale;
}

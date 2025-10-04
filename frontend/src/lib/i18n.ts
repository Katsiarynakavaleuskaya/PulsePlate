export function getClientLocale(): string {
  if (typeof window === 'undefined') {
    return 'en';
  }

  const raw = navigator.language || 'en';
  const normalized = raw ? (raw.split("-")[0] ?? "").toLowerCase() : "";

  return normalized || 'en';
}

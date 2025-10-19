/**
 * Get the client's locale from browser navigator.language.
 *
 * @returns The normalized locale string (e.g., 'en', 'es', 'ru') or 'en' as fallback
 */
export function getClientLocale(): string {
  if (typeof window === 'undefined') {
    return 'en';
  }

  const raw = navigator.language || 'en';
  const normalized = raw.split('-')[0].toLowerCase();

  return normalized || 'en';
}

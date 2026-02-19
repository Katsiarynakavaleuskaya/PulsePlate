// RU: Компонент Soft Paywall Hook - отображает предложение PRO функций после BMI расчета
// EN: Soft Paywall Hook component - displays PRO feature offer after BMI calculation

import { useNavigate } from 'react-router-dom';
import type { components } from '../../api/schema';

interface SoftPaywallHookProps {
  hook?: components['schemas']['SoftPaywallHook'] | null;
  onCtaClick?: () => void;
}

/**
 * Soft Paywall Hook component.
 *
 * IMPORTANT: No BMI-dependent logic. Renders backend contract only.
 * - Uses default_* fields from backend (no i18n lookup)
 * - No hardcoded text
 * - No BMI value/category conditions
 *
 * @param hook - Soft paywall hook data from backend (optional, null-safe)
 * @param onCtaClick - Optional custom CTA handler (defaults to navigate to /pro)
 */
export default function SoftPaywallHook({ hook, onCtaClick }: SoftPaywallHookProps): JSX.Element | null {
  const navigate = useNavigate();

  // Guard: do not render if hook is null/undefined
  if (!hook) {
    return null;
  }

  // Guard: do not render if availability is false (backend should return null, but guard)
  if (!hook.availability?.pro_available) {
    return null;
  }

  const handleClick = (): void => {
    if (onCtaClick) {
      onCtaClick();
    } else {
      // Default: navigate to /pro (paywall page)
      navigate('/pro');
    }
  };

  return (
    <div
      className="rounded-2xl border p-6 shadow-sm"
      style={{
        background:
          'linear-gradient(180deg, var(--color-surface) 0%, var(--color-surface-muted) 100%)',
        borderColor: 'var(--color-border)',
      }}
    >
      <h3 className="mb-2 text-lg font-semibold text-text">
        {hook.message.default_title}
      </h3>
      <p className="mb-5 text-muted">
        {hook.message.default_body}
      </p>
      <button
        type="button"
        onClick={handleClick}
        className="min-h-[44px] rounded-full bg-primary px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary/90"
        data-testid="soft-paywall-cta"
      >
        {hook.message.default_cta}
      </button>
    </div>
  );
}

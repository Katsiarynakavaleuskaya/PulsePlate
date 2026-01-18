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
    <div className="bg-white rounded-xl p-6 shadow-sm border border-primary/20">
      <h3 className="text-lg font-semibold text-text mb-2">
        {hook.message.default_title}
      </h3>
      <p className="text-muted mb-4">
        {hook.message.default_body}
      </p>
      <button
        type="button"
        onClick={handleClick}
        className="px-4 py-2 bg-primary text-navy rounded-lg hover:bg-primary/90 transition-colors font-medium"
        data-testid="soft-paywall-cta"
      >
        {hook.message.default_cta}
      </button>
    </div>
  );
}

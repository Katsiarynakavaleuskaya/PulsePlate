// RU: Компонент Soft Paywall Hook - отображает предложение PRO функций после BMI расчета
// EN: Soft Paywall Hook component - displays PRO feature offer after BMI calculation

import { useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import type { components } from '../../api/schema';
import { createAnalyticsEventId, logPaywallExposure } from '../../lib/analytics';

const BMI_SOFT_PAYWALL_SOURCE = 'bmi_soft_paywall';
const BMI_SOFT_PAYWALL_TRIGGER_REASON = 'post_bmi_result';

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
  const exposureIdRef = useRef<string | null>(null);
  const hookIdRef = useRef<string | null>(null);
  const hasLoggedShownRef = useRef(false);
  const hookId = hook?.id ?? null;
  const isRenderable = Boolean(hook?.availability?.pro_available);

  useEffect(() => {
    if (!isRenderable || !hookId) {
      hookIdRef.current = null;
      exposureIdRef.current = null;
      hasLoggedShownRef.current = false;
      return;
    }

    if (hookIdRef.current !== hookId) {
      hookIdRef.current = hookId;
      exposureIdRef.current = createAnalyticsEventId();
      hasLoggedShownRef.current = false;
    }
  }, [hookId, isRenderable]);

  const safeLogPaywallEvent = useCallback(
    (eventName: 'shown' | 'cta_clicked'): void => {
      if (!hook || !isRenderable) {
        return;
      }

      try {
        logPaywallExposure({
          client_event_id: createAnalyticsEventId(),
          exposure_id: exposureIdRef.current ?? createAnalyticsEventId(),
          event_name: eventName,
          source_surface: BMI_SOFT_PAYWALL_SOURCE,
          trigger_reason: BMI_SOFT_PAYWALL_TRIGGER_REASON,
          via: 'soft_paywall_hook',
          metadata: {
            hook_id: hook.id,
            position: hook.position,
            target: hook.target,
          },
        });
      } catch {
        // RU: Ошибки analytics не должны ломать teaser/paywall UX.
        // EN: Analytics failures must never break teaser/paywall UX.
      }
    },
    [hook, isRenderable]
  );

  useEffect(() => {
    if (!isRenderable || !hookId || hasLoggedShownRef.current) {
      return;
    }
    safeLogPaywallEvent('shown');
    hasLoggedShownRef.current = true;
  }, [hookId, isRenderable, safeLogPaywallEvent]);

  // Guard: do not render if hook is null/undefined
  if (!hook) {
    return null;
  }

  // Guard: do not render if availability is false (backend should return null, but guard)
  if (!hook.availability?.pro_available) {
    return null;
  }

  const handleClick = (): void => {
    safeLogPaywallEvent('cta_clicked');
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

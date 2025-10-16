/**
 * VIP Feature Component
 *
 * Example component that demonstrates VIP feature flag integration.
 * This component will only render when VIP module is enabled.
 */

import React, { useState, useRef, useEffect, useId } from 'react';
import { useTranslation } from 'react-i18next';
import { useVipModule } from '../lib/useFeatureFlag';
import Paywall from './Paywall/BeforeAfter';

interface VipFeatureProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

/**
 * VIP Feature wrapper component
 *
 * @param children - Content to show when VIP is enabled
 * @param fallback - Content to show when VIP is disabled (optional)
 *
 * @example
 * ```typescript
 * <VipFeature fallback={<PremiumGate />}>
 *   <AdvancedAnalytics />
 * </VipFeature>
 * ```
 */
export const VipFeature: React.FC<VipFeatureProps> = ({ children, fallback = null }) => {
  const isVipEnabled = useVipModule();

  if (!isVipEnabled) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};

/**
 * VIP Badge component
 *
 * Shows a VIP badge when VIP module is enabled
 */
export const VipBadge: React.FC<{
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'outline' | 'subtle';
}> = ({ size = 'md', variant = 'default' }) => {
  const isVipEnabled = useVipModule();

  if (!isVipEnabled) {
    return null;
  }

  const sizeClasses = {
    sm: 'px-1.5 py-0.5 text-xs',
    md: 'px-2 py-1 text-xs',
    lg: 'px-3 py-1.5 text-sm'
  };

  const variantClasses = {
    default: 'bg-gradient-to-r from-purple-500 to-pink-500 text-white',
    outline: 'border border-purple-500 text-purple-600 dark:text-purple-400',
    subtle: 'bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200'
  };

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full ${sizeClasses[size]} ${variantClasses[variant]}`}
      role="img"
      aria-label="VIP status"
    >
      VIP
    </span>
  );
};

/**
 * VIP Gate component
 *
 * Renders content behind a VIP gate that either shows children directly for VIP users
 * or presents a de-emphasized, non-interactive preview with a CTA to open a paywall.
 *
 * Similar to PremiumGate but for VIP features.
 */
export const VipGate: React.FC<{
  isVip: boolean;
  children: React.ReactNode;
  source?: string;
}> = ({ isVip, children, source = "unknown" }) => {
  const [open, setOpen] = useState(false);
  const { t } = useTranslation();
  const previewRef = useRef<HTMLDivElement | null>(null);
  const describedById = useId();

  useEffect(() => {
    const root = previewRef.current;
    if (!root) {
      return;
    }

    // Feature-detect inert support explicitly
    const hasInertSupport = 'inert' in HTMLElement.prototype ||
                           ('inert' in root && typeof (root as any).inert === 'boolean');

    if (hasInertSupport) {
      // Use native inert when supported
      const prevInert = (root as any).inert;
      (root as any).inert = true;
      return () => {
        (root as any).inert = prevInert;
      };
    } else {
      // Fallback: set aria-hidden and remove tabindex from descendants
      root.setAttribute("aria-hidden", "true");
      const focusables = root.querySelectorAll<HTMLElement>(
        'a, button, input, textarea, select, details, [tabindex]'
      );
      focusables.forEach((el) => {
        if (el.hasAttribute("tabindex")) {
          el.setAttribute("data-pp-prev-tabindex", el.getAttribute("tabindex") || "");
        }
        el.setAttribute("tabindex", "-1");
        if ("disabled" in el && !(el as HTMLButtonElement).disabled) {
          (el as HTMLButtonElement).disabled = true;
          el.setAttribute("data-pp-disabled", "true");
        }
      });
      return () => {
        root.removeAttribute("aria-hidden");
        const restore = root.querySelectorAll<HTMLElement>(
          '[data-pp-prev-tabindex], [tabindex="-1"], [data-pp-disabled]'
        );
        restore.forEach((el) => {
          const prev = el.getAttribute("data-pp-prev-tabindex");
          if (prev !== null) {
            if (prev === "") {
              el.removeAttribute("tabindex");
            } else {
              el.setAttribute("tabindex", prev);
            }
            el.removeAttribute("data-pp-prev-tabindex");
          } else if (el.getAttribute("tabindex") === "-1") {
            el.removeAttribute("tabindex");
          }
          if (el.getAttribute("data-pp-disabled") === "true") {
            (el as HTMLButtonElement).disabled = false;
            el.removeAttribute("data-pp-disabled");
          }
        });
      };
    }
  }, []);

  if (isVip) return <>{children}</>;

  return (
    <>
      <div
        ref={previewRef}
        {...({ inert: true } as any)}
        className="opacity-60 pointer-events-none"
        aria-label="VIP gated content"
      >
        {children}
      </div>

      {/* Offscreen description to give AT context while preview remains aria-hidden/inert */}
      <p id={describedById} className="sr-only">
        {t("vip.title")} — {t("vip.subtitle")}
      </p>

      <button
        type="button"
        className="mt-3 px-4 py-2 rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:opacity-90 transition-opacity"
        onClick={() => {
          setOpen(true);
        }}
        aria-haspopup="dialog"
        aria-describedby={describedById}
        style={{ minHeight: 44 }}
      >
        {t("vip.cta")}
      </button>

      {open && (
        <Paywall
          source={source}
          via="vip_cta"
          onClose={() => {
            setOpen(false);
          }}
          onPurchase={() => {
            // hook for VIP purchase flow
          }}
        />
      )}
    </>
  );
};

/**
 * VIP Layout Components
 *
 * Basic layout components for VIP pages and features
 */

/**
 * VIP Page Header component
 */
export const VipPageHeader: React.FC<{
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
}> = ({ title, subtitle, children }) => {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-3 mb-2">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{title}</h1>
        <VipBadge size="lg" />
      </div>
      {subtitle && (
        <p className="text-gray-600 dark:text-gray-400">{subtitle}</p>
      )}
      {children}
    </div>
  );
};

/**
 * VIP Feature Card component
 */
export const VipFeatureCard: React.FC<{
  title: string;
  description: string;
  icon?: React.ReactNode;
  children?: React.ReactNode;
}> = ({ title, description, icon, children }) => {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-start gap-4">
        {icon && (
          <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg flex items-center justify-center text-white">
            {icon}
          </div>
        )}
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            {title}
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            {description}
          </p>
          {children}
        </div>
      </div>
    </div>
  );
};

/**
 * VIP Section component
 */
export const VipSection: React.FC<{
  title: string;
  children: React.ReactNode;
  className?: string;
}> = ({ title, children, className = "" }) => {
  return (
    <section className={`mb-8 ${className}`}>
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
        {title}
      </h2>
      {children}
    </section>
  );
};

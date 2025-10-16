import React, { useState, useId } from 'react';
import { useTranslation } from 'react-i18next';
import { useVipModule } from '../lib/useFeatureFlag';
import { useInert } from '../lib/useInert';
import Paywall from './Paywall/BeforeAfter';

export interface VipGateProps {
  isVip?: boolean;
  children?: React.ReactNode;
  source?: string;
  message?: string; // Legacy prop for backward compatibility
}

/**
 * VIP Gate component
 *
 * Renders content behind a VIP gate that either shows children directly for VIP users
 * or presents a de-emphasized, non-interactive preview with a CTA to open a paywall.
 *
 * Similar to PremiumGate but for VIP features.
 *
 * @param isVip - If true, renders children without gating. If not provided, uses useVipModule hook.
 * @param children - Content to render inside the gate or preview.
 * @param source - Optional source identifier forwarded to the Paywall.
 * @param message - Optional custom message (legacy prop for backward compatibility).
 */
export const VipGate: React.FC<VipGateProps> = ({ isVip, children, source = "unknown", message }) => {
  // Use hook if isVip is not provided (backward compatibility)
  const hookVipStatus = useVipModule();
  const actualIsVip = isVip ?? hookVipStatus;
  const [open, setOpen] = useState(false);
  const { t } = useTranslation();
  const previewRef = useInert(!actualIsVip);
  const describedById = useId();

  // If no children provided, render legacy gate UI
  if (!children) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center">
        <div className="w-16 h-16 mb-4 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
          <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          VIP Feature
        </h3>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          {message || t("vip.subtitle")}
        </p>
        <button
          type="button"
          className="px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:opacity-90 transition-opacity"
          aria-label="Upgrade to VIP access"
          onClick={() => {
            setOpen(true);
          }}
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
      </div>
    );
  }

  if (actualIsVip) return <>{children}</>;

  return (
    <>
      <div
        ref={previewRef}
        className="opacity-60 pointer-events-none"
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

import React, { useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useInert } from "../lib/useInert";
import { purchasePremium } from "../lib/paywallPurchase";
import { useTelemetry } from "../lib/useTelemetry";
import Paywall from "./Paywall/BeforeAfter";
// import { log, Events } from "../lib/analytics"; // TODO: Add analytics when needed

type Props = {
  isPremium: boolean;
  children: React.ReactNode;
  source?: string;
};

/**
 * Renders content behind a premium gate that either shows children directly for premium users or presents a de-emphasized, non-interactive preview with a CTA to open a paywall.
 *
 * When gating is active, the component prevents interaction and focus on the preview content for assistive and keyboard users (using native `inert` when available, with an aria-hidden/tabindex fallback) and exposes an accessible CTA that opens the Paywall dialog.
 *
 * @param isPremium - If `true`, renders `children` without gating.
 * @param children - Content to render inside the gate or preview.
 * @param source - Optional source identifier forwarded to the Paywall; defaults to `"unknown"`.
 * @returns The PremiumGate React element containing either the unmodified children (for premium users) or a gated preview with a CTA and paywall dialog.
 */
export default function PremiumGate({ isPremium, children, source = "unknown" }: Props) {
  const [open, setOpen] = useState(false);
  const { t } = useTranslation();
  const { track } = useTelemetry();
  const previewRef = useInert(!isPremium);
  const describedById = useId();
  const ctaRef = useRef<HTMLButtonElement | null>(null);

  const restoreCtaFocus = (): void => {
    const el = ctaRef.current;
    queueMicrotask(() => {
      if (el && document.contains(el)) {
        el.focus();
      }
    });
  };

  if (isPremium) return <>{children}</>;

  return (
    <>
      <div ref={previewRef} className="pointer-events-none opacity-70 saturate-75">
        {children}
      </div>

      {/* Offscreen description to give AT context while preview remains aria-hidden/inert */}
      <p id={describedById} className="sr-only">
        {t("paywall.title")} — {t("paywall.subtitle")}
      </p>

      <button
        ref={ctaRef}
        type="button"
        className="mt-3 inline-flex min-h-11 items-center justify-center rounded-xl bg-[var(--color-primary)] px-4 py-2 font-semibold text-[var(--color-primary-foreground)] shadow-sm transition-colors hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] focus-visible:ring-offset-2"
        onClick={() => {
          track.gateInteracted("premium_preview", "click");
          track.upgradeClicked(source, "premium_preview_gate");
          setOpen(true);
        }}
        aria-haspopup="dialog"
        aria-describedby={describedById}
      >
        {t("paywall.cta")}
      </button>

      {open && (
        <Paywall
          source={source}
          via="paywall_cta"
          onClose={() => {
            track.paywallDismissed(source, "close_button");
            setOpen(false);
            restoreCtaFocus();
          }}
          onPurchase={async () => {
            await purchasePremium({ source, via: "paywall_cta" });
            track.upgradeClicked(source, "paywall");
            setOpen(false);
            restoreCtaFocus();
          }}
        />
      )}
    </>
  );
}

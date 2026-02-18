import React, { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { useInert } from "../lib/useInert";
import { purchasePremium } from "../lib/paywallPurchase";
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
  const previewRef = useInert(!isPremium);
  const describedById = useId();

  if (isPremium) return <>{children}</>;

  return (
    <>
      <div
        ref={previewRef}
        {...({ inert: true } as any)}
        className="opacity-60 pointer-events-none"
        aria-label="Premium gated content"
      >
        {children}
      </div>

      {/* Offscreen description to give AT context while preview remains aria-hidden/inert */}
      <p id={describedById} className="sr-only">
        {t("paywall.title")} — {t("paywall.subtitle")}
      </p>

      <button
        type="button"
        className="mt-3 px-4 py-2 rounded-xl bg-[var(--pp-primary)] text-white"
        onClick={() => {
          setOpen(true);
        }}
        aria-haspopup="dialog"
        aria-describedby={describedById}
        style={{ minHeight: 44 }}
      >
        {t("paywall.cta")}
      </button>

      {open && (
        <Paywall
          source={source}
          via="paywall_cta"
          onClose={() => {
            setOpen(false);
          }}
          onPurchase={async () => {
            await purchasePremium({ source, via: "paywall_cta" });
            setOpen(false);
          }}
        />
      )}
    </>
  );
}

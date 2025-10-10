import React, { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
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
      // Use native inert when supported - set as string attribute to avoid React warnings
      const prevInert = root.getAttribute('inert');
      root.setAttribute('inert', '');
      return () => {
        if (prevInert !== null) {
          root.setAttribute('inert', prevInert);
        } else {
          root.removeAttribute('inert');
        }
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

  if (isPremium) return <>{children}</>;

  return (
    <>
      <div
        ref={previewRef}
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
          onPurchase={() => {
            // hook for purchase flow
          }}
        />
      )}
    </>
  );
}

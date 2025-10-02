import React, { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import Paywall from "./Paywall/BeforeAfter";

type Props = {
  isPremium: boolean;
  children: React.ReactNode;
  source?: string;
};

type InertibleElement = HTMLElement & { inert?: boolean };

type StoredState = {
  previousTabIndex: string | null;
  previousDisabled: boolean;
};

function applyFallbackInert(root: HTMLElement): () => void {
  root.setAttribute("aria-hidden", "true");
  const state = new WeakMap<HTMLElement, StoredState>();
  const focusables = root.querySelectorAll<HTMLElement>(
    "a, button, input, textarea, select, details, [tabindex]"
  );

  focusables.forEach((element) => {
    const previousTabIndex = element.getAttribute("tabindex");
    const previousDisabled = "disabled" in element && Boolean((element as HTMLButtonElement).disabled);
    state.set(element, { previousTabIndex, previousDisabled });

    element.setAttribute("tabindex", "-1");
    element.setAttribute("data-pp-disabled", previousDisabled ? "true" : "false");

    if ("disabled" in element && !previousDisabled) {
      (element as HTMLButtonElement).disabled = true;
    }
  });

  return () => {
    root.removeAttribute("aria-hidden");

    focusables.forEach((element) => {
      const stored = state.get(element);
      if (!stored) return;

      const { previousTabIndex, previousDisabled } = stored;
      if (previousTabIndex === null) {
        element.removeAttribute("tabindex");
      } else {
        element.setAttribute("tabindex", previousTabIndex);
      }

      if ("disabled" in element && !previousDisabled) {
        (element as HTMLButtonElement).disabled = false;
      }

      element.removeAttribute("data-pp-disabled");
    });
  };
}

export default function PremiumGate({ isPremium, children, source = "unknown" }: Props) {
  const [open, setOpen] = useState(false);
  const { t } = useTranslation();
  const previewRef = useRef<HTMLDivElement | null>(null);
  const describedById = useId();

  useEffect(() => {
    const root = previewRef.current;
    if (!root) return;

    const elementWithInert = root as InertibleElement;
    const supportsInert = "inert" in elementWithInert;

    if (supportsInert) {
      const previous = elementWithInert.inert ?? false;
      elementWithInert.inert = true;
      return () => {
        elementWithInert.inert = previous;
      };
    }

    return applyFallbackInert(root);
  }, [previewRef]);

  useEffect(() => {
    const root = previewRef.current as InertibleElement | null;
    if (!root) return;
    if ("inert" in root) {
      root.setAttribute("data-pp-inert", String(open));
    }
  }, [open]);

  if (isPremium) return <>{children}</>;

  return (
    <>
      <div
        ref={previewRef}
        aria-hidden="true"
        data-pp-inert={open ? "true" : "false"}
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

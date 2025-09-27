import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Events, log } from "../../lib/analytics";

type Props = {
  onClose: () => void;
  onPurchase?: () => void;
};

function useFocusTrap() {
  return (container: HTMLElement | null, event: React.KeyboardEvent) => {
    if (!container || event.key !== "Tab") {
      return;
    }
    const focusables = container.querySelectorAll<HTMLElement>(
      'a[href], button, textarea, input, select, [tabindex]:not([tabindex="-1"])'
    );
    if (focusables.length === 0) {
      return;
    }
    const first = focusables[0];
    const last = focusables[focusables.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };
}

export default function BeforeAfter({ onClose, onPurchase }: Props) {
  const { t } = useTranslation();
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const primaryButtonRef = useRef<HTMLButtonElement | null>(null);
  const trap = useFocusTrap();

  useEffect(() => {
    log(Events.PAYWALL_VIEW);
    primaryButtonRef.current?.focus();
  }, []);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="paywall-title"
      className="fixed inset-0 grid place-items-center bg-black/60 p-4"
      onKeyDown={(event) => trap(dialogRef.current, event)}
    >
      <div ref={dialogRef} className="w-full max-w-md rounded-xl bg-white text-black p-5">
        <h2 id="paywall-title" className="text-2xl mb-1">
          {t("paywall.title")}
        </h2>
        <p className="text-sm text-gray-600 mb-4">{t("paywall.subtitle")}</p>

        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="border rounded-lg p-3">
            <div className="text-xs uppercase text-gray-500">{t("paywall.before")}</div>
            <ul className="text-sm list-disc list-inside">
              <li>Random plate</li>
              <li>Macros only</li>
              <li>Manual shopping</li>
            </ul>
          </div>
          <div className="border rounded-lg p-3 border-[var(--pp-gold)]">
            <div className="text-xs uppercase text-gray-500">{t("paywall.after")}</div>
            <ul className="text-sm list-disc list-inside">
              <li>Personal plate</li>
              <li>Micro-balance</li>
              <li>Auto shopping list</li>
            </ul>
          </div>
        </div>

        <button
          ref={primaryButtonRef}
          className="w-full py-3 rounded-xl"
          style={{ background: "var(--pp-primary)", color: "white", minHeight: 44 }}
          onClick={() => {
            log(Events.PURCHASE_ATTEMPT);
            onPurchase?.();
          }}
        >
          {t("paywall.cta")}
        </button>

        <button
          className="w-full py-2 mt-2 rounded-xl"
          style={{ minHeight: 44 }}
          onClick={() => {
            log(Events.PURCHASE_CANCEL);
            onClose();
          }}
        >
          {t("common.cancel")}
        </button>

        <p className="mt-3 text-xs text-gray-500">{t("paywall.legal")}</p>
      </div>
    </div>
  );
}

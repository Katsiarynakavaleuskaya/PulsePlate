import { useCallback, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Events, log } from "../../lib/analytics";
import { useFocusTrap } from "../../lib/useFocusTrap";

type Props = {
  onClose: () => void;
  onPurchase?: () => void;
};

export default function BeforeAfter({ onClose, onPurchase }: Props) {
  const { t } = useTranslation();
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const primaryButtonRef = useRef<HTMLButtonElement | null>(null);
  const trap = useFocusTrap(dialogRef);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }

      trap(event);
    },
    [onClose, trap]
  );

  useEffect(() => {
    log(Events.PAYWALL_VIEW);
    primaryButtonRef.current?.focus();
  }, []);

  // RU: Закрытие по Escape с аналитикой.
  // EN: Close on Escape with analytics logging.
  useEffect(() => {
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        log(Events.PURCHASE_CANCEL, { via: "escape" });
        onClose();
      }
    };
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="paywall-title"
      className="fixed inset-0 grid place-items-center bg-black/60 p-4"
      onKeyDown={handleKeyDown}
    >
      <div ref={dialogRef} className="w-full max-w-md rounded-xl bg-white text-black p-5">
        <h2 id="paywall-title" className="text-2xl mb-1">
          {t("paywall.title")}
        </h2>
        <p className="text-sm text-gray-600 mb-4">{t("paywall.subtitle")}</p>

        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="border rounded-lg p-3">
            <div className="text-xs uppercase text-gray-500">{t("paywall.before.label")}</div>
            <ul className="text-sm list-disc list-inside">
              {[
                "paywall.items.before.random_plate",
                "paywall.items.before.macros_only",
                "paywall.items.before.manual_shopping",
              ].map((key) => (
                <li key={key}>{t(key)}</li>
              ))}
            </ul>
          </div>
          <div className="border rounded-lg p-3 border-[var(--pp-gold)]">
            <div className="text-xs uppercase text-gray-500">{t("paywall.after.label")}</div>
            <ul className="text-sm list-disc list-inside">
              {[
                "paywall.items.after.personal_plate",
                "paywall.items.after.micro_balance",
                "paywall.items.after.auto_shopping_list",
              ].map((key) => (
                <li key={key}>{t(key)}</li>
              ))}
            </ul>
          </div>
        </div>

        <button
          type="button"
          ref={primaryButtonRef}
          className="w-full py-3 rounded-xl bg-[var(--pp-primary)] text-white"
          style={{ minHeight: 44 }}
          onClick={() => {
            log(Events.PURCHASE_ATTEMPT);
            onPurchase?.();
          }}
        >
          {t("paywall.cta")}
        </button>

        <button
          type="button"
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

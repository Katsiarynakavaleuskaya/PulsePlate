import React, { useCallback, useEffect, useId, useRef } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import { useTranslation } from "react-i18next";
import { Events, log, logError } from "../../lib/analytics";
import { useFocusTrap } from "../../lib/useFocusTrap";

type Props = {
  onClose: () => void;
  onPurchase?: () => void;
  source?: string;
  via?: string;
};

export default function BeforeAfter({ onClose, onPurchase, source = "unknown", via = "paywall" }: Props) {
  const { t } = useTranslation();
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const primaryButtonRef = useRef<HTMLButtonElement | null>(null);
  const titleId = useId();
  const trap = useFocusTrap(dialogRef);

  const handleKeyDown = useCallback(
    (event: ReactKeyboardEvent<HTMLDivElement>) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        try {
          log(Events.PURCHASE_CANCEL, { source, via });
        } catch (err) {
          logError(err);
        }
        onClose();
        return;
      }

      trap(event);
    },
    [onClose, trap, source, via]
  );

  // Analytics effect - separate from focus management
  useEffect(() => {
    try {
      // Ensure analytics errors never break the paywall rendering
      log(Events.PAYWALL_VIEW, { source, via });
    } catch (err) {
      logError(err);
    }
  }, [source, via]);

  // Focus effect - only on mount to avoid stealing focus on prop changes
  useEffect(() => {
    primaryButtonRef.current?.focus();
  }, []);

  // Note: Escape handling is confined to the dialog's keydown handler.

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      className="fixed inset-0 grid place-items-center bg-black/60 p-4"
      onKeyDown={handleKeyDown}
    >
      <div ref={dialogRef} className="w-full max-w-md rounded-xl bg-white text-black p-5">
        <h2 id={titleId} className="text-2xl mb-1">
          {t("paywall.title")}
        </h2>
        <p className="text-sm text-gray-600 mb-4">{t("paywall.subtitle")}</p>

        <div className="grid grid-cols-2 gap-3 mb-4">
          {([
            {
              label: "paywall.sections.before.label",
              features: [
                ["paywall.sections.before.features.randomPlate", "paywall.sections.before.features.randomDescription"],
                ["paywall.sections.before.features.macrosOnly", "paywall.sections.before.features.macrosDescription"],
                ["paywall.sections.before.features.manualShopping", "paywall.sections.before.features.manualDescription"],
              ],
              toneClass: "border",
            },
            {
              label: "paywall.sections.after.label",
              features: [
                ["paywall.sections.after.features.personalPlate", "paywall.sections.after.features.personalDescription"],
                ["paywall.sections.after.features.microBalance", "paywall.sections.after.features.microDescription"],
                ["paywall.sections.after.features.autoShoppingList", "paywall.sections.after.features.autoDescription"],
              ],
              toneClass: "border border-[var(--pp-gold)]",
            },
          ] as const).map(({ label, features, toneClass }) => (
            <div key={label} className={`${toneClass} rounded-lg p-3`}>
              <div className="text-xs uppercase text-gray-500">{t(label)}</div>
              <ul className="text-sm list-disc list-inside">
                {features.map(([featureKey, descriptionKey]) => (
                  <li key={featureKey} className="space-y-1">
                    <div>{t(featureKey)}</div>
                    <p className="text-xs text-gray-500">{t(descriptionKey)}</p>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <button
          type="button"
          ref={primaryButtonRef}
          className="w-full py-3 rounded-xl bg-pp-primary text-white"
          style={{ minHeight: 44 }}
          data-testid="paywall-cta"
          onClick={() => {
            // Fire-and-forget analytics before invoking callback
            try {
              log(Events.PURCHASE_ATTEMPT, { source, via });
            } catch (err) {
              logError(err);
            }
            onPurchase?.();
          }}
        >
          {t("paywall.cta")}
        </button>

        <button
          type="button"
          className="w-full py-2 mt-2 rounded-xl"
          style={{ minHeight: 44 }}
          data-testid="paywall-cancel"
          onClick={() => {
            try {
              log(Events.PURCHASE_CANCEL, { source, via });
            } catch (err) {
              logError(err);
            }
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

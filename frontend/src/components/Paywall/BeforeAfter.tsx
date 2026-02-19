import { useCallback, useEffect, useRef } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import { useTranslation } from "react-i18next";
import { Events, log } from "../../lib/analytics";
import { useFocusTrap } from "../../lib/useFocusTrap";

type Props = {
  onClose: () => void;
  onPurchase?: () => void;
  purchaseLabel?: string;
  purchaseDisabled?: boolean;
  source?: string;
  via?: string;
};

const beforeItems = [
  "paywall.items.before.random_plate",
  "paywall.items.before.macros_only",
  "paywall.items.before.manual_shopping",
] as const;

const afterItems = [
  "paywall.items.after.personal_plate",
  "paywall.items.after.micro_balance",
  "paywall.items.after.auto_shopping_list",
] as const;

const plans = [
  { name: "Free", subtitle: "Basics", highlighted: false },
  { name: "Pro", subtitle: "Best value", highlighted: true },
  { name: "VIP", subtitle: "Advanced", highlighted: false },
] as const;

/**
 * Renders a modal paywall dialog showing before/after feature lists with primary purchase and cancel actions.
 *
 * The dialog traps focus, sets initial focus to the primary CTA on mount, and handles Escape to close.
 * Analytics events for view, purchase attempt, and cancel are issued but errors from analytics are ignored.
 *
 * @param onClose - Callback invoked when the dialog should close (Escape key or Cancel).
 * @param onPurchase - Optional callback invoked when the primary purchase CTA is activated.
 * @param source - Optional identifier for analytics `source` (defaults to `"unknown"`).
 * @param via - Optional identifier for analytics `via` (defaults to `"paywall"`).
 * @returns The React element for the paywall dialog.
 */
export default function BeforeAfter({
  onClose,
  onPurchase,
  purchaseLabel,
  purchaseDisabled = false,
  source = "unknown",
  via = "paywall",
}: Props) {
  const { t } = useTranslation();
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const primaryButtonRef = useRef<HTMLButtonElement | null>(null);
  const cancelButtonRef = useRef<HTMLButtonElement | null>(null);
  const trap = useFocusTrap(dialogRef);

  const handleKeyDown = useCallback(
    (event: ReactKeyboardEvent<HTMLDivElement>) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        try {
          log(Events.PURCHASE_CANCEL, { source, via });
        } catch {
            // Ignore analytics errors
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
    } catch {
      // swallow analytics SDK errors
    }
  }, [source, via]);

  // Body scroll lock effect - only on mount/unmount
  useEffect(() => {
    // Prevent background scrolling when modal is open
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    // Cleanup: restore scroll when modal closes
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  // Focus effect - reactive to purchaseDisabled changes
  useEffect(() => {
    // Set focus on primary button, or fallback to Cancel if CTA is disabled
    if (purchaseDisabled) {
      cancelButtonRef.current?.focus();
    } else {
      primaryButtonRef.current?.focus();
    }
  }, [purchaseDisabled]);

  // Note: Escape handling is confined to the dialog's keydown handler.

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="paywall-title"
      className="fixed inset-0 grid place-items-center bg-black/60 p-4"
      onKeyDown={handleKeyDown}
    >
      <div
        ref={dialogRef}
        className="flex w-full max-w-md max-h-[85vh] flex-col overflow-hidden rounded-2xl bg-white text-black shadow-xl"
      >
        <div className="overflow-y-auto p-5">
          <div className="mb-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4">
            <div className="mb-2 inline-flex items-center rounded-full bg-[var(--color-surface)] px-3 py-1 text-xs font-semibold text-[var(--color-primary)]">
              PRO
            </div>
            <h2 id="paywall-title" className="text-2xl mb-1">
              {t("paywall.title")}
            </h2>
            <p className="text-sm text-gray-600">{t("paywall.subtitle")}</p>
          </div>

          <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="rounded-xl border border-[var(--color-border)] p-3">
              <div className="text-xs uppercase text-gray-500">{t("paywall.before.label")}</div>
              <ul className="mt-2 text-sm list-disc list-inside space-y-1">
                {beforeItems.map((key) => (
                  <li key={key}>{t(key)}</li>
                ))}
              </ul>
            </div>
            <div className="rounded-xl border border-[var(--pp-gold)] bg-[var(--color-surface-muted)] p-3">
              <div className="text-xs uppercase text-gray-500">{t("paywall.after.label")}</div>
              <ul className="mt-2 text-sm list-disc list-inside space-y-1">
                {afterItems.map((key) => (
                  <li key={key}>{t(key)}</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="mb-4 grid grid-cols-3 gap-2 text-center text-xs">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={`rounded-lg p-2 ${
                  plan.highlighted
                    ? "border border-[var(--color-primary)] bg-[var(--color-surface-muted)]"
                    : "border border-[var(--color-border)]"
                }`}
              >
                <div
                  className={`font-semibold ${
                    plan.highlighted ? "text-[var(--color-primary)]" : "text-gray-700"
                  }`}
                >
                  {plan.name}
                </div>
                <div className={plan.highlighted ? "text-gray-600" : "text-gray-500"}>
                  {plan.subtitle}
                </div>
              </div>
            ))}
          </div>

          <p className="text-xs text-gray-500">{t("paywall.legal")}</p>
        </div>

        <div className="border-t border-[var(--color-border)] bg-white p-4">
          <button
            type="button"
            ref={primaryButtonRef}
            className="w-full rounded-xl bg-pp-primary py-3 text-white disabled:cursor-not-allowed disabled:opacity-50"
            style={{ minHeight: 44 }}
            data-testid="paywall-cta"
            disabled={purchaseDisabled}
            aria-disabled={purchaseDisabled}
            onClick={() => {
              if (purchaseDisabled) return;
              // Fire-and-forget analytics before invoking callback
              try {
                log(Events.PURCHASE_ATTEMPT, { source, via });
              } catch {
                // Ignore analytics errors
              }
              onPurchase?.();
            }}
          >
            {purchaseLabel ?? t("paywall.cta")}
          </button>

          <button
            type="button"
            ref={cancelButtonRef}
            className="mt-2 w-full rounded-xl py-2 text-sm text-gray-700"
            style={{ minHeight: 44 }}
            data-testid="paywall-cancel"
            onClick={() => {
              try {
                log(Events.PURCHASE_CANCEL, { source, via });
              } catch {
                // Ignore analytics errors
              }
              onClose();
            }}
          >
            {t("common.cancel")}
          </button>
        </div>
      </div>
    </div>
  );
}

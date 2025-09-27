import { useState } from "react";
import { useTranslation } from "react-i18next";
import Paywall from "./Paywall/BeforeAfter";
import { log, Events } from "../lib/analytics";

type Props = {
  isPremium: boolean;
  children: React.ReactNode;
  source?: string;
};

export default function PremiumGate({ isPremium, children, source = "unknown" }: Props) {
  const [open, setOpen] = useState(false);
  const { t } = useTranslation();

  if (isPremium) return <>{children}</>;

  return (
    <>
      <div aria-label="Premium gated content" className="opacity-60 pointer-events-none" inert>
        {children}
      </div>
      <button
        type="button"
        className="mt-3 px-4 py-2 rounded-xl bg-[var(--pp-primary)] text-white"
        aria-label={t("paywall.title")}
        onClick={() => {
          setOpen(true);
        }}
        aria-haspopup="dialog"
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

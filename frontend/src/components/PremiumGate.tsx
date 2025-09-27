import { useState } from "react";
import Paywall from "./Paywall/BeforeAfter";
import { log, Events } from "../lib/analytics";

type Props = {
  isPremium: boolean;
  children: React.ReactNode;
  source?: string;
};

export default function PremiumGate({ isPremium, children, source = "unknown" }: Props) {
  const [open, setOpen] = useState(false);

  if (isPremium) return <>{children}</>;

  return (
    <>
      <div aria-label="Premium gated content" className="opacity-60 pointer-events-none">
        {children}
      </div>
      <button
        className="mt-3 px-4 py-2 rounded-xl bg-[var(--pp-primary)] text-white"
        onClick={() => {
          log(Events.PURCHASE_ATTEMPT, { source });
          setOpen(true);
        }}
        aria-haspopup="dialog"
        style={{ minHeight: 44 }}
      >
        Unlock Premium
      </button>

      {open && (
        <Paywall
          onClose={() => {
            log(Events.PURCHASE_CANCEL, { source });
            setOpen(false);
          }}
          onPurchase={() => {
            // RU: здесь будет платёж/бридж; пока — лог.
            // EN: hook for purchase/bridge; for now — log only.
            log(Events.PURCHASE_ATTEMPT, { source, via: "paywall_cta" });
          }}
        />
      )}
    </>
  );
}

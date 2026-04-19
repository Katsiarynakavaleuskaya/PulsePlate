import { useEffect, useState } from "react";
import { getProSessionStatus } from "../api/client";
import { PREMIUM_CHANGE_EVENT } from "./premiumEvents";

// RU: Premium truth читается только из серверной session contract.
// EN: Premium truth is derived only from the server-side session contract.
export function usePremium(): boolean | undefined {
  const [isPremium, setIsPremium] = useState<boolean | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;

    const sync = async (): Promise<void> => {
      const session = await getProSessionStatus().catch(() => null);
      if (!cancelled) {
        setIsPremium(session?.tier === "PRO" || session?.tier === "VIP");
      }
    };

    void sync();
    window.addEventListener(PREMIUM_CHANGE_EVENT, sync as EventListener);
    return () => {
      cancelled = true;
      window.removeEventListener(PREMIUM_CHANGE_EVENT, sync as EventListener);
    };
  }, []);

  return isPremium;
}

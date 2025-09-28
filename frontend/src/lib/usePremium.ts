import { useEffect, useState } from "react";

// Simple premium membership hook.
// In a real app, replace localStorage reads with your auth/user store selector.
export function usePremium(): boolean | undefined {
  const [isPremium, setIsPremium] = useState<boolean | undefined>(undefined);

  useEffect(() => {
    const read = (): boolean => {
      try {
        const raw = localStorage.getItem("pp_premium");
        if (raw === null) return false;
        return raw === "true";
      } catch {
        return false;
      }
    };

    const sync = () => {
      setIsPremium(read());
    };

    // Initial read
    sync();

    // Cross-document updates
    const onStorage = (e: StorageEvent) => {
      if (e.key === "pp_premium") {
        setIsPremium(e.newValue === "true");
      }
    };

    // Same-document updates via custom event
    const onCustom = () => sync();

    window.addEventListener("storage", onStorage);
    window.addEventListener("pp-premium-change", onCustom as EventListener);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("pp-premium-change", onCustom as EventListener);
    };
  }, []);

  return isPremium;
}

import { useEffect, useState } from "react";

// Simple premium membership hook.
// In a real app, replace localStorage reads with your auth/user store selector.
export function usePremium(): boolean | undefined {
  const [isPremium, setIsPremium] = useState<boolean | undefined>(undefined);

  useEffect(() => {
    function read(): boolean {
      try {
        const raw = localStorage.getItem("pp_premium");
        if (raw === null) return false;
        return raw === "true";
      } catch {
        return false;
      }
    }

    setIsPremium(read());

    const onStorage = (e: StorageEvent) => {
      if (e.key === "pp_premium") {
        setIsPremium(e.newValue === "true");
      }
    };

    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return isPremium;
}

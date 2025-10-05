import { createContext, useCallback, useMemo, type ReactNode } from "react";
import { api as apiBase } from "../api/client";
import { useToast } from "../components/ui/useToast";
import { useApiKey } from "../settings/useApiKey";

export type AuthContextType = {
  apiKey?: string;
  setApiKey: (value: string) => void;
  clearApiKey: () => void;
  apiJson: typeof apiBase;
};

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const toast = useToast();
  const { apiKey, setApiKey, clearApiKey } = useApiKey();

  const apiJson = useCallback(<T,>(path: string, options?: Parameters<typeof apiBase>[1]) => {
    const originalOnAuthError = options?.onAuthError;

    return apiBase<T>(path, {
      ...(options ?? {}),
      onAuthError: (code, ctx) => {
        toast.error(code === 401 ? "Неверный или отсутствующий API-ключ." : "Доступ запрещён (403).");
        originalOnAuthError?.(code, ctx);
      },
    });
  }, [toast]);

  const value = useMemo<AuthContextType>(() => ({ apiKey, setApiKey, clearApiKey, apiJson }), [apiKey, setApiKey, clearApiKey, apiJson]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

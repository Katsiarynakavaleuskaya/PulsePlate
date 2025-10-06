import React, { createContext, useMemo, useCallback } from "react";
import { api as apiBase } from "../api/client";
import { getToastHelpers } from "../components/ui/useToast";
import { useApiKey } from "../settings/useApiKey";

type AuthContextType = {
  apiKey?: string;
  setApiKey: (k: string) => void;
  clearApiKey: () => void;
  apiJson: typeof apiBase;
};

export const AuthContext = createContext<AuthContextType>(null!);

export const AuthProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const toast = getToastHelpers();
  const { apiKey, setApiKey, clearApiKey } = useApiKey();

  // общий onAuthError → решение принимает UI: тост + soft-гейтинг
  const apiJson = useCallback<typeof apiBase>((url, opts = {}) => {
    return apiBase(url, {
      ...opts,
      onAuthError: (code, ctx) => {
        toast.error(code === 401 ? "Неверный или отсутствующий API-ключ." : "Доступ запрещён (403).");
        // можно не очищать ключ автоматически — оставим пользователю выбор
        // при желании: ctx.clearApiKey();
        opts.onAuthError?.(code, ctx);
      },
    });
  }, [toast]);

  const value = useMemo(() => ({ apiKey, setApiKey, clearApiKey, apiJson }), [apiKey, setApiKey, clearApiKey, apiJson]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

import React, { createContext, useContext, useMemo, useCallback } from "react";
import { api as apiBase } from "../api/client";
import { useToast } from "../components/ui/useToast";
import { useApiKey } from "../settings/useApiKey";
import { useTranslation } from "react-i18next";

type AuthContextType = {
  apiKey?: string;
  setApiKey: (k: string) => void;
  clearApiKey: () => void;
  apiJson: typeof apiBase;
};

/**
 * Auth context that provides API key management and authenticated API client.
 * Will be non-null only when wrapped by AuthProvider. Consuming components must be
 * wrapped by AuthProvider or perform null checks. Using outside provider risks
 * runtime errors. See RequireKey.tsx for an example guard component.
 */
export const AuthContext = createContext<AuthContextType>(null!);

export const AuthProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const { apiKey, setApiKey, clearApiKey } = useApiKey();
  const { t } = useTranslation();
  const toast = useToast();

  // shared onAuthError handler → UI decides response: toast + soft-gating
  const apiJson = useCallback<typeof apiBase>((url, opts = {}) => {
    return apiBase(url, {
      ...opts,
      onAuthError: (code, ctx) => {
        toast.error(code === 401 ? t("auth.invalidApiKey") : t("auth.accessDenied"));
        // We don't clear the key automatically — leave the choice to the user
        // If desired: ctx.clearApiKey();
        opts.onAuthError?.(code, ctx);
      },
    });
  }, [t, toast]);

  const value = useMemo(() => ({ apiKey, setApiKey, clearApiKey, apiJson }), [apiKey, setApiKey, clearApiKey, apiJson]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

/**
 * Hook to access authentication context. Must be used within AuthProvider.
 */
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};

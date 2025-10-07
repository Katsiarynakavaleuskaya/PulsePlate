import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  type ReactNode,
} from "react";
import { useTranslation } from "react-i18next";
import { api as apiBase } from "../api/client";
import { useToast } from "../components/ui/useToast";
import { useApiKey } from "../settings/useApiKey";

const MIN_API_KEY_LENGTH = 20;

export class AuthError extends Error {
  code: string;

  constructor(code: string, message?: string) {
    super(message);
    this.name = "AuthError";
    this.code = code;
  }
}

export interface AuthContextType {
  apiKey: string | null;
  isAuthenticated: boolean;
  setApiKey: (key: string) => void;
  clearApiKey: () => void;
  apiJson: typeof apiBase;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const toast = useToast();
  const { t } = useTranslation();
  const { apiKey, setApiKey: storeSetKey, clearApiKey: storeClearKey } = useApiKey();

  const setApiKey = useCallback(
    (value: string) => {
      const trimmed = value.trim();
      if (trimmed.length < MIN_API_KEY_LENGTH) {
        throw new AuthError("API_KEY_TOO_SHORT");
      }
      if (!/^[A-Za-z0-9_-]+$/.test(trimmed)) {
        throw new AuthError("API_KEY_INVALID_FORMAT");
      }
      storeSetKey(trimmed);
    },
    [storeSetKey]
  );

  const clearApiKey = useCallback(() => {
    storeClearKey();
  }, [storeClearKey]);

  const apiJson = useCallback<typeof apiBase>(
    (path, opts = {}) =>
      apiBase(path, {
        ...opts,
        onAuthError: () => {
          storeClearKey();
          toast.error(t("auth.errors.unauthorized"));
        },
      }),
    [storeClearKey, toast, t]
  );

  const value = useMemo<AuthContextType>(
    () => ({
      apiKey: apiKey ?? null,
      isAuthenticated: Boolean(apiKey),
      setApiKey,
      clearApiKey,
      apiJson,
    }),
    [apiKey, setApiKey, clearApiKey, apiJson]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

export { AuthContext };

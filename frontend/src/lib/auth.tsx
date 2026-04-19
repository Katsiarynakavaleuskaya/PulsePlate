import { createContext, useContext, useState, useEffect, useRef, useCallback, ReactNode } from 'react';
import { getStoredApiKey, clearStoredApiKey } from '../auth/storage';
import { checkProSession, clearProSession, exchangeApiKeyForSession } from '../api/client';
import { dispatchPremiumChangeEvent } from './premiumEvents';

const MIN_API_KEY_LENGTH = 20;
const AUTH_PROMPT_DELAY_MS = 500;
const SESSION_BOOTSTRAP_TIMEOUT_MS = 5000;
const SESSION_AUTH_SENTINEL = '__session_auth__';

export class AuthError extends Error {
  code: string;

  constructor(code: string, message?: string) {
    super(message);
    this.name = 'AuthError';
    this.code = code;
    Object.setPrototypeOf(this, AuthError.prototype);
  }
}

export interface AuthContextType {
  apiKey: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setApiKey: (key: string, remember?: boolean) => Promise<void>;
  clearApiKey: () => Promise<void>;
  showAuthPrompt: boolean;
  setShowAuthPrompt: (show: boolean) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

async function withTimeout<T>(promise: Promise<T>, timeoutMs: number, fallbackValue: T): Promise<T> {
  let timeoutId: number | null = null;
  const guardedPromise = (async (): Promise<T> => {
    try {
      return await promise;
    } catch {
      return fallbackValue;
    }
  })();
  const timeoutPromise = new Promise<T>((resolve) => {
    timeoutId = window.setTimeout(() => {
      resolve(fallbackValue);
    }, timeoutMs);
  });

  try {
    return await Promise.race([guardedPromise, timeoutPromise]);
  } finally {
    if (timeoutId !== null) {
      window.clearTimeout(timeoutId);
    }
  }
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [apiKey, setApiKeyState] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [showAuthPrompt, setShowAuthPrompt] = useState(false);
  const promptTimeoutRef = useRef<number | null>(null);

  const clearPromptTimeout = useCallback(() => {
    if (promptTimeoutRef.current !== null) {
      clearTimeout(promptTimeoutRef.current);
      promptTimeoutRef.current = null;
    }
  }, []);

  const scheduleAuthPrompt = useCallback(() => {
    clearPromptTimeout();
    promptTimeoutRef.current = window.setTimeout(() => {
      setShowAuthPrompt(true);
    }, AUTH_PROMPT_DELAY_MS);
  }, [clearPromptTimeout]);

  useEffect(() => {
    let cancelled = false;

    const initializeAuth = async () => {
      // One-time migration: exchange legacy browser key for secure server session cookie.
      const legacyKey = getStoredApiKey();
      if (legacyKey) {
        try {
          await withTimeout(
            exchangeApiKeyForSession(legacyKey),
            SESSION_BOOTSTRAP_TIMEOUT_MS,
            false,
          );
        } catch {
          // Fail closed: migration best-effort, auth state is derived from session check below.
        } finally {
          // Always clear legacy persistence even if exchange fails.
          clearStoredApiKey();
        }
      }

      const sessionActive = await withTimeout(
        checkProSession(),
        SESSION_BOOTSTRAP_TIMEOUT_MS,
        false,
      );
      if (cancelled) {
        return;
      }

      setIsAuthenticated(sessionActive);
      setApiKeyState(sessionActive ? SESSION_AUTH_SENTINEL : null);
      setIsLoading(false);
      dispatchPremiumChangeEvent();
      if (!sessionActive) {
        scheduleAuthPrompt();
      } else {
        clearPromptTimeout();
        setShowAuthPrompt(false);
      }
    };

    void initializeAuth();

    return () => {
      cancelled = true;
      clearPromptTimeout();
    };
  }, [clearPromptTimeout, scheduleAuthPrompt]);

  const setApiKey = async (key: string, _remember: boolean = false) => {
    const trimmedKey = key.trim();
    if (trimmedKey.length < MIN_API_KEY_LENGTH) {
      throw new AuthError('API_KEY_TOO_SHORT');
    }
    if (!/^[A-Za-z0-9_-]+$/.test(trimmedKey)) {
      throw new AuthError('API_KEY_INVALID_FORMAT');
    }
    clearPromptTimeout();

    const exchanged = await exchangeApiKeyForSession(trimmedKey);
    if (!exchanged) {
      throw new AuthError('API_KEY_INVALID');
    }

    const sessionActive = await checkProSession();
    if (!sessionActive) {
      throw new AuthError('SESSION_NOT_ESTABLISHED');
    }

    clearStoredApiKey();
    setIsAuthenticated(true);
    setApiKeyState(SESSION_AUTH_SENTINEL);
    setShowAuthPrompt(false);
    dispatchPremiumChangeEvent();
  };

  const clearApiKey = async () => {
    clearPromptTimeout();
    clearStoredApiKey();
    try {
      await clearProSession();
    } catch {
      // Best-effort logout: local auth state is still cleared deterministically.
    }
    setIsAuthenticated(false);
    setApiKeyState(null);
    dispatchPremiumChangeEvent();
    scheduleAuthPrompt();
  };

  const value: AuthContextType = {
    apiKey,
    isAuthenticated,
    isLoading,
    setApiKey,
    clearApiKey,
    showAuthPrompt,
    setShowAuthPrompt,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

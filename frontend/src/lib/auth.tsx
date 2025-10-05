import React, { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import { getStoredApiKey, setStoredApiKey, clearStoredApiKey } from '../api/client';

interface AuthContextType {
  apiKey: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setApiKey: (key: string, remember?: boolean) => void;
  clearApiKey: () => void;
  showAuthPrompt: boolean;
  setShowAuthPrompt: (show: boolean) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [apiKey, setApiKeyState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showAuthPrompt, setShowAuthPrompt] = useState(false);
  const promptTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    // Load API key from storage on mount
    const storedKey = getStoredApiKey();
    setApiKeyState(storedKey);
    setIsLoading(false);

    // Show auth prompt if no key is stored
    if (!storedKey) {
      // Delay showing prompt to avoid flash on initial load
      promptTimeoutRef.current = window.setTimeout(() => {
        // Double-check that no key was set during the delay
        const currentKey = getStoredApiKey();
        if (!currentKey) {
          setShowAuthPrompt(true);
        }
      }, 500);
    }

    return () => {
      if (promptTimeoutRef.current !== null) {
        clearTimeout(promptTimeoutRef.current);
        promptTimeoutRef.current = null;
      }
    };
  }, []);

  const setApiKey = (key: string, remember: boolean = false) => {
    const trimmedKey = key.trim();
    // Increase minimum length to 20 characters
    if (trimmedKey.length < 20) {
      throw new Error('auth.apiKey.tooShort');
    }
    // Add format check: only allow alphanumeric, dashes, and underscores
    if (!/^[A-Za-z0-9_-]+$/.test(trimmedKey)) {
      throw new Error('auth.apiKey.invalidFormat');
    }
    if (promptTimeoutRef.current !== null) {
      clearTimeout(promptTimeoutRef.current);
      promptTimeoutRef.current = null;
    }
    setStoredApiKey(trimmedKey, remember);
    setApiKeyState(trimmedKey);
    setShowAuthPrompt(false);
  };

  const clearApiKey = () => {
    if (promptTimeoutRef.current !== null) {
      clearTimeout(promptTimeoutRef.current);
      promptTimeoutRef.current = null;
    }
    clearStoredApiKey();
    setApiKeyState(null);
    setShowAuthPrompt(true);
  };

  const value: AuthContextType = {
    apiKey,
    isAuthenticated: !!apiKey,
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

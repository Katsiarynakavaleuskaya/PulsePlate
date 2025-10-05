import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
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

  useEffect(() => {
    // Load API key from storage on mount
    const storedKey = getStoredApiKey();
    setApiKeyState(storedKey);
    setIsLoading(false);

    // Show auth prompt if no key is stored
    if (!storedKey) {
      setShowAuthPrompt(true);
    }
  }, []);

  const setApiKey = (key: string, remember: boolean = false) => {
    setStoredApiKey(key, remember);
    setApiKeyState(key);
    setShowAuthPrompt(false);
  };

  const clearApiKey = () => {
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

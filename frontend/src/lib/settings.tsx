import React, { createContext, useContext, ReactNode } from 'react';

// Settings context for future use - currently no settings are implemented
interface SettingsContextType {
  // Placeholder for future settings
  settings: Record<string, never>;
  updateSetting: <K extends keyof Record<string, never>>(key: K, value: Record<string, never>[K]) => void;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

interface SettingsProviderProps {
  children: ReactNode;
}

const initialSettings = {} as const;

export function SettingsProvider({ children }: SettingsProviderProps) {
  const updateSetting = <K extends keyof typeof initialSettings>(key: K, value: typeof initialSettings[K]) => {
    // Placeholder implementation - no settings currently implemented
    console.warn(`Setting "${key}" not implemented yet`);
  };

  const value: SettingsContextType = {
    settings: initialSettings,
    updateSetting,
  };

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings(): SettingsContextType {
  const context = useContext(SettingsContext);
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
}

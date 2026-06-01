import { createContext, useContext, ReactNode, useState } from 'react';
import type { GuidedPlanningDraft } from '../features/guidedPlanning/planningPreview';
import type { SetupFormValues } from '../pages/NutritionSetup/schema';

export interface Settings {
  setup?: SetupFormValues;
  guidedPlanningDraft?: GuidedPlanningDraft;
}

interface SettingsContextType {
  settings: Settings;
  updateSetting: <K extends keyof Settings>(key: K, value: Settings[K]) => void;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

interface SettingsProviderProps {
  children: ReactNode;
}

const initialSettings: Settings = {};

export function SettingsProvider({ children }: SettingsProviderProps) {
  const [settings, setSettings] = useState<Settings>(initialSettings);

  const updateSetting = <K extends keyof Settings>(key: K, value: Settings[K]) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const value: SettingsContextType = {
    settings,
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

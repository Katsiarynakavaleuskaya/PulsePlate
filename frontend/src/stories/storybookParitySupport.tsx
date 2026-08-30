import { useLayoutEffect, type PropsWithChildren } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import {
  PRO_SESSION_PATH,
  setApiClientDependencies,
  type ProSessionStatus,
} from '../api/client';
import { AuthProvider } from '../lib/auth';
import { SettingsProvider } from '../lib/settings';
import { DesignSystemCanvas, PanelShell } from '../components/design-system/shared';
import Home from '../pages/Home';
import NutritionSetupPage from '../pages/NutritionSetup';
import ResultView from '../pages/NutritionSetup/ResultView';
import type { SetupFormValues } from '../pages/NutritionSetup/schema';
import ProPaywallPage from '../pages/Pro/ProPaywallPage';

export type StorySessionState = 'guest' | 'pro' | 'vip';

const STORYBOOK_API_BASE = 'https://storybook.pulseplate.local';
const CBT_INSIGHT_PATH = '/api/v1/pro/cbt/insight';
const BMR_PATH = '/api/v1/pro/nutrition/bmr';
const PLATE_PATH = '/api/v1/pro/nutrition/plate';
const TARGETS_PATH = '/api/v1/pro/nutrition/targets';

export const storySetupValues: SetupFormValues = {
  sex: 'female',
  age: 34,
  height_cm: 168,
  weight_kg: 64,
  activity: 'moderate',
  goal: 'maintain',
  diet_flags: ['HIGH_PROTEIN', 'MEDITERRANEAN'],
};

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function sessionPayload(sessionState: StorySessionState): ProSessionStatus | null {
  if (sessionState === 'guest') {
    return null;
  }

  return {
    status: 'ok',
    authenticated: true,
    auth_source: 'cookie',
    tier: sessionState === 'vip' ? 'VIP' : 'PRO',
  };
}

function storybookPathname(requestUrl: string): string {
  return new URL(requestUrl, STORYBOOK_API_BASE).pathname;
}

function isStorybookApiRequest(requestUrl: string): boolean {
  const url = new URL(requestUrl, STORYBOOK_API_BASE);
  const storybookOrigin = new URL(STORYBOOK_API_BASE).origin;
  return url.origin === storybookOrigin && url.pathname.startsWith('/api/');
}

function routeStorybookResponse(requestUrl: string, sessionState: StorySessionState): Response {
  const pathname = storybookPathname(requestUrl);

  if (pathname === PRO_SESSION_PATH) {
    const payload = sessionPayload(sessionState);
    return payload ? jsonResponse(payload) : jsonResponse({ detail: 'No active story session' }, 401);
  }

  if (pathname === CBT_INSIGHT_PATH) {
    return jsonResponse({
      insight: 'Keep dinner protein-forward and repeat one reliable meal to reduce decision fatigue.',
      confidence: 0.92,
      uncertainty: 0.08,
      rag_used: true,
      sources: [
        {
          chunk_id: 'storybook-cbt-1',
          file: 'docs/cbt/storybook-parity.md',
          preview: 'Small repeatable patterns keep guidance calm and non-clinical.',
          score: 0.97,
        },
      ],
      warnings: ['Storybook fixture only; not a live coaching response.'],
      mode: 'storybook-safe',
      quota_state: 'fixture',
    });
  }

  if (pathname === BMR_PATH) {
    return jsonResponse({
      bmr: { mifflin: 1390, harris: 1420 },
      tdee: { mifflin: 2154, harris: 2201 },
      activity_level: 'moderate',
      recommended_intake: {
        maintenance: 2154,
        weight_loss: 1723.2,
        weight_gain: 2584.8,
      },
      formulas_used: ['mifflin', 'harris'],
      notes: ['Storybook deterministic fixture'],
    });
  }

  if (pathname === PLATE_PATH) {
    return jsonResponse({
      kcal: 2154,
      macros: {
        protein_g: 132,
        carbs_g: 242,
        fat_g: 72,
        fiber_g: 31,
      },
      portions: {
        protein_palm: 2.1,
        fat_thumbs: 1.3,
        carb_cups: 3.2,
        veg_cups: 3,
      },
      layout: [
        { kind: 'plate_sector', fraction: 0.25, label: 'Protein', tooltip: 'Lean protein' },
        { kind: 'plate_sector', fraction: 0.45, label: 'Carbs', tooltip: 'Whole grains' },
        { kind: 'plate_sector', fraction: 0.3, label: 'Fats', tooltip: 'Healthy fats' },
      ],
      meals: [],
      meals_per_day: 3,
    });
  }

  if (pathname === TARGETS_PATH) {
    return jsonResponse({
      kcal_daily: 2154,
      macros: { protein_g: 132, carbs_g: 242, fat_g: 72 },
      water_ml: 2400,
      priority_micros: {
        iron_mg: 18,
        calcium_mg: 1000,
        vitamin_d_iu: 600,
      },
      activity_weekly: { minutes: 150 },
      calculation_date: '2026-04-30',
      warnings: [],
    });
  }

  return jsonResponse(
    {
      detail: `Unhandled Storybook API fixture: ${pathname}`,
      storybook_fixture: true,
    },
    500
  );
}

export function StorybookApiStub({
  children,
  sessionState = 'pro',
}: PropsWithChildren<{ sessionState?: StorySessionState }>) {
  useLayoutEffect(() => {
    const originalFetch = window.fetch.bind(window);

    setApiClientDependencies({
      getStoredApiKey: () => null,
      clearStoredApiKey: () => undefined,
      apiBase: STORYBOOK_API_BASE,
    });

    const stubFetch = (async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const requestUrl =
        typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
      if (isStorybookApiRequest(requestUrl)) {
        return routeStorybookResponse(requestUrl, sessionState);
      }
      return originalFetch(input, init);
    }) as typeof window.fetch;

    window.fetch = stubFetch;

    return () => {
      if (window.fetch === stubFetch) {
        window.fetch = originalFetch;
      }
      setApiClientDependencies(null);
    };
  }, [sessionState]);

  return <>{children}</>;
}

export function HomeStorySurface({ sessionState }: { sessionState: StorySessionState }) {
  return (
    <StorybookApiStub sessionState={sessionState}>
      <AuthProvider>
        <SettingsProvider>
          <MemoryRouter initialEntries={['/app']}>
            <Home />
          </MemoryRouter>
        </SettingsProvider>
      </AuthProvider>
    </StorybookApiStub>
  );
}

export function NutritionSetupFormStorySurface() {
  return (
    <SettingsProvider>
      <DesignSystemCanvas>
        <PanelShell
          title="Nutrition setup profile form"
          subtitle="Storybook review surface for the implemented setup form state."
          className="overflow-hidden"
        >
          <div className="rounded-3xl border border-white/10 bg-[var(--color-bg)] p-4">
            <NutritionSetupPage />
          </div>
        </PanelShell>
      </DesignSystemCanvas>
    </SettingsProvider>
  );
}

export function NutritionSetupResultStorySurface() {
  return (
    <StorybookApiStub sessionState="pro">
      <MemoryRouter initialEntries={['/setup']}>
        <DesignSystemCanvas>
          <PanelShell
            title="Nutrition setup calculated results"
            subtitle="Deterministic Storybook fixture for the implemented result state; no live backend is used."
            className="overflow-hidden"
          >
            <div className="rounded-3xl border border-white/10 bg-[var(--color-bg)] p-4">
              <ResultView values={storySetupValues} onEdit={() => undefined} />
            </div>
          </PanelShell>
        </DesignSystemCanvas>
      </MemoryRouter>
    </StorybookApiStub>
  );
}

export function ProProductInfoStorySurface() {
  return (
    <StorybookApiStub sessionState="pro">
      <MemoryRouter initialEntries={['/pro']}>
        <Routes>
          <Route path="/pro" element={<ProPaywallPage />} />
        </Routes>
      </MemoryRouter>
    </StorybookApiStub>
  );
}

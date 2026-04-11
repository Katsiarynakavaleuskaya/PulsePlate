import type { JSX, PropsWithChildren } from 'react';
import { useEffect } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { setApiClientDependencies, type ProSessionStatus } from '../api/client';
import { DesignSystemCanvas, PanelShell } from '../components/design-system/shared';

export type PlateSessionState = 'pro' | 'locked';

const STORYBOOK_API_BASE = 'https://storybook.pulseplate.local';

function buildSessionPayload(sessionState: PlateSessionState): ProSessionStatus | null {
  if (sessionState === 'locked') {
    return null;
  }

  return {
    status: 'ok',
    authenticated: true,
    auth_source: 'cookie',
    tier: 'PRO',
  };
}

function installPlateSessionStub(sessionState: PlateSessionState): () => void {
  const originalFetch = window.fetch.bind(window);

  setApiClientDependencies({
    getStoredApiKey: () => null,
    clearStoredApiKey: () => undefined,
    apiBase: STORYBOOK_API_BASE,
  });

  window.fetch = (async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const requestUrl = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
    if (requestUrl.endsWith('/api/v1/pro/session')) {
      const payload = buildSessionPayload(sessionState);
      const status = payload ? 200 : 401;
      return new Response(payload ? JSON.stringify(payload) : null, {
        status,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return originalFetch(input, init);
  }) as typeof window.fetch;

  return () => {
    window.fetch = originalFetch;
    setApiClientDependencies(null);
  };
}

export function PlateStoryHarness({
  sessionState,
  children,
}: PropsWithChildren<{ sessionState: PlateSessionState }>): JSX.Element {
  useEffect(() => installPlateSessionStub(sessionState), [sessionState]);

  return (
    <MemoryRouter initialEntries={['/plate']}>
      <DesignSystemCanvas>
        <PanelShell
          title="Web plate baseline"
          subtitle="Representative parity-pack review surface for the web.plate page with deterministic session state."
          className="overflow-hidden"
        >
          <div className="min-h-[780px] rounded-3xl border border-white/10 bg-[var(--color-bg)]">
            {children}
          </div>
        </PanelShell>
      </DesignSystemCanvas>
    </MemoryRouter>
  );
}

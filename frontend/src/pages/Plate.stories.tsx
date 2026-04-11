import type { JSX, PropsWithChildren } from 'react';
import { useEffect } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { MemoryRouter } from 'react-router-dom';
import '../i18n';
import { setApiClientDependencies, type ProSessionStatus } from '../api/client';
import { DesignSystemCanvas, PanelShell } from '../components/design-system/shared';
import Plate from './Plate';

type PlateSessionState = 'pro' | 'locked';
const STORYBOOK_API_BASE = 'https://storybook.pulseplate.local';

let activePlateStorySessionState: PlateSessionState | null = null;
let restorePlateStorySessionStub: (() => void) | null = null;

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

function installPlateStorySessionStub(sessionState: PlateSessionState): void {
  if (activePlateStorySessionState === sessionState && restorePlateStorySessionStub) {
    return;
  }

  restorePlateStorySessionStub?.();

  const originalFetch = window.fetch.bind(window);

  // RU: Подменяем API base и fetch синхронно до mount дочернего Story.
  // EN: Install API base and fetch stub synchronously before the child Story mounts.
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

  activePlateStorySessionState = sessionState;
  restorePlateStorySessionStub = () => {
    window.fetch = originalFetch;
    setApiClientDependencies(null);
    activePlateStorySessionState = null;
    restorePlateStorySessionStub = null;
  };
}

function PlateStoryHarness({
  sessionState,
  children,
}: PropsWithChildren<{ sessionState: PlateSessionState }>): JSX.Element {
  installPlateStorySessionStub(sessionState);

  useEffect(() => {
    return () => {
      restorePlateStorySessionStub?.();
    };
  }, []);

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

const meta = {
  title: 'PulsePlate/Parity Pack/Plate',
  component: Plate,
  render: (): JSX.Element => <Plate />,
  decorators: [
    (Story, context): JSX.Element => (
      <PlateStoryHarness sessionState={(context.parameters.sessionState as PlateSessionState | undefined) ?? 'pro'}>
        <Story />
      </PlateStoryHarness>
    ),
  ],
  parameters: {
    layout: 'fullscreen',
    sessionState: 'pro',
  },
} satisfies Meta<typeof Plate>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ProUnlocked: Story = {};

export const SessionLocked: Story = {
  parameters: {
    sessionState: 'locked',
  },
};

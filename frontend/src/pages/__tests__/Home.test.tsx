import { JSX } from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { axe } from 'jest-axe';
import Home from '../Home';
import { RequireKey } from '../../auth/RequireKey';
import { routes, type RoutePath } from '../../config/routes';
import {
  guidedPlanningObservabilitySensitiveFields,
  setGuidedPlanningEventSink,
  type GuidedPlanningEvent,
} from '../../lib/mvpObservability';

vi.mock('../../lib/auth', () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from '../../lib/auth';

interface EnterKeyLocationState {
  from?: { pathname?: string };
}

function EnterKeyProbe(): JSX.Element {
  const location = useLocation();
  const fromPath = (location.state as EnterKeyLocationState | null)?.from?.pathname ?? 'none';
  return <div data-testid="enter-key-probe">{fromPath}</div>;
}

function renderConfiguredRoute(path: RoutePath, element: JSX.Element): JSX.Element {
  const routeConfig = routes.find((route) => route.path === path);
  if (!routeConfig) {
    throw new Error(`Missing route config for ${path}`);
  }

  return routeConfig.requiresAuth ? <RequireKey>{element}</RequireKey> : element;
}

function renderHomeRoutes(): ReturnType<typeof render> {
  return render(
    <MemoryRouter initialEntries={['/app']}>
      <Routes>
        <Route path="/app" element={renderConfiguredRoute('/app', <Home />)} />
        <Route
          path="/setup"
          element={renderConfiguredRoute('/setup', <div data-testid="setup-route">Nutrition Setup Flow</div>)}
        />
        <Route
          path="/plate"
          element={renderConfiguredRoute('/plate', <div data-testid="plate-route">Plate route</div>)}
        />
        <Route
          path="/progress"
          element={renderConfiguredRoute('/progress', <div data-testid="progress-route">Progress route</div>)}
        />
        <Route path="/bmi" element={renderConfiguredRoute('/bmi', <div data-testid="bmi-route">BMI route</div>)} />
        <Route path="/pro" element={renderConfiguredRoute('/pro', <div data-testid="pro-route">Pro route</div>)} />
        <Route path="/enter-key" element={renderConfiguredRoute('/enter-key', <EnterKeyProbe />)} />
      </Routes>
    </MemoryRouter>
  );
}

describe('Home Guided Planning Preview', () => {
  const guidedPlanningEvents: GuidedPlanningEvent[] = [];

  beforeEach(() => {
    guidedPlanningEvents.length = 0;
    setGuidedPlanningEventSink((event) => guidedPlanningEvents.push(event));
    vi.mocked(useAuth).mockReturnValue({
      apiKey: null,
      isAuthenticated: false,
      isLoading: false,
      setApiKey: vi.fn(),
      clearApiKey: vi.fn(),
      showAuthPrompt: false,
      setShowAuthPrompt: vi.fn(),
    });
  });

  afterEach(() => {
    setGuidedPlanningEventSink(null);
    cleanup();
    vi.clearAllMocks();
  });

  it('renders the planning-first MVP surface on /app', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByTestId('guided-planning-preview')).toBeInTheDocument();
    expect(screen.getByTestId('mvp-accessibility-evidence')).toHaveTextContent(/selector groups/i);
    expect(screen.getByTestId('mvp-observability-evidence')).toHaveTextContent(/frontend-only interaction evidence/i);
    expect(screen.getByRole('heading', { level: 1, name: 'Turn a check-in into practical meal decisions.' })).toBeInTheDocument();
    expect(screen.getByText('check-in')).toBeInTheDocument();
    expect(screen.getByText('targets')).toBeInTheDocument();
    expect(screen.getByText('daily plate')).toBeInTheDocument();
    expect(screen.getByText('weekly plan')).toBeInTheDocument();
    expect(screen.getByText('shopping list')).toBeInTheDocument();
  });

  it('renders required observability anchors', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    expect(screen.getByTestId('planning-intent-selector')).toBeInTheDocument();
    expect(screen.getByTestId('planning-time-selector')).toBeInTheDocument();
    expect(screen.getByTestId('planning-preview-card')).toBeInTheDocument();
    expect(screen.getByTestId('tier-value-rail')).toBeInTheDocument();
    expect(screen.getByTestId('wellness-boundary-note')).toBeInTheDocument();
    expect(screen.getByTestId('primary-planning-cta')).toBeInTheDocument();
  });

  it('emits safe frontend-only MVP view evidence on render', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    expect(guidedPlanningEvents.map((event) => event.name)).toEqual([
      'guided_planning_viewed',
      'planning_preview_seen',
      'tier_value_viewed',
      'tier_value_viewed',
      'tier_value_viewed',
      'wellness_boundary_viewed',
    ]);
    expect(guidedPlanningEvents).toEqual(
      expect.arrayContaining([
        {
          name: 'guided_planning_viewed',
          payload: { surface: 'app', componentId: 'guided-planning-preview', routePath: '/app' },
        },
        {
          name: 'planning_preview_seen',
          payload: { surface: 'app', componentId: 'planning-preview-card', routePath: '/app' },
        },
        {
          name: 'wellness_boundary_viewed',
          payload: { surface: 'app', componentId: 'wellness-boundary-note', routePath: '/app' },
        },
      ])
    );
    expect(guidedPlanningEvents.filter((event) => event.name === 'tier_value_viewed').map((event) => event.payload.tierLabel)).toEqual([
      'FREE',
      'PRO',
      'VIP',
    ]);
  });

  it('keeps emitted MVP event payloads free of sensitive fields', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    await user.click(screen.getByRole('button', { name: /Shopping-list planning/i }));
    await user.click(screen.getByRole('button', { name: /Batch prep/i }));
    await user.click(screen.getByTestId('primary-planning-cta'));

    const payloadKeys = guidedPlanningEvents.flatMap((event) => Object.keys(event.payload));
    expect(payloadKeys).not.toEqual(expect.arrayContaining([...guidedPlanningObservabilitySensitiveFields]));
    expect(guidedPlanningEvents.every((event) => event.payload.surface === 'app')).toBe(true);
  });

  it('lets users choose planning intent and practical time constraint', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    await user.click(screen.getByRole('button', { name: /Shopping-list planning/i }));
    await user.click(screen.getByRole('button', { name: /Batch prep/i }));

    expect(screen.getByRole('group', { name: 'Choose your planning intent' })).toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'Pick a practical constraint' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Shopping-list planning/i })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /Batch prep/i })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /More consistent meals/i })).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByRole('button', { name: /Shopping-list planning/i })).toHaveAttribute(
      'aria-controls',
      'planning-preview-card-region'
    );
    expect(screen.getByText('Translate check-in intent into meal anchors first, then shop around those anchors.')).toBeInTheDocument();
    expect(screen.getByText('Batch-prep mode highlights repeatable proteins, grains, and produce that can be reused.')).toBeInTheDocument();
    expect(guidedPlanningEvents).toEqual(
      expect.arrayContaining([
        {
          name: 'planning_intent_selected',
          payload: {
            surface: 'app',
            componentId: 'planning-intent-selector',
            routePath: '/app',
            optionId: 'shopping',
          },
        },
        {
          name: 'planning_time_selected',
          payload: {
            surface: 'app',
            componentId: 'planning-time-selector',
            routePath: '/app',
            optionId: 'batch',
          },
        },
      ])
    );
  });

  it('shows the FREE PRO VIP value ladder honestly', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    expect(screen.getByText('Check-in and baseline preview')).toBeInTheDocument();
    expect(screen.getByText('Targets, daily plate, saved weekly plan')).toBeInTheDocument();
    expect(screen.getAllByText('Recipes, menu flows, shopping/export')).toHaveLength(2);
    expect(screen.getByText('Preview example')).toBeInTheDocument();
  });

  it('shows wellness boundary and avoids forbidden medical claim copy', () => {
    const { container } = render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    expect(screen.getByText('Wellness planning support only. Not medical advice.')).toBeInTheDocument();
    expect(screen.getByRole('note', { name: 'Wellness planning support only. Not medical advice.' })).toBeInTheDocument();
    expect(container).not.toHaveTextContent(
      /diagnose|treat|cure|guaranteed weight loss|AI doctor|personalized medical recommendation|clinically proven|prescription|disease management|medical-grade|therapeutic recommendation/i
    );
  });

  it('links primary and secondary planning CTAs to safe existing routes', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    expect(screen.getByTestId('primary-planning-cta')).toHaveAttribute('href', '/setup');
    expect(screen.getByRole('link', { name: 'Continue planning' })).toHaveAttribute('href', '/setup');
    expect(screen.getByRole('link', { name: 'Learn why this is wellness-only' })).toHaveAttribute(
      'href',
      '#wellness-boundary'
    );
  });

  it('navigates to setup flow from the primary CTA', async () => {
    const user = userEvent.setup();

    renderHomeRoutes();

    await user.click(screen.getByTestId('primary-planning-cta'));

    expect(screen.getByTestId('setup-route')).toBeInTheDocument();
    expect(screen.queryByTestId('enter-key-probe')).not.toBeInTheDocument();
    expect(guidedPlanningEvents).toEqual(
      expect.arrayContaining([
        {
          name: 'primary_planning_cta_clicked',
          payload: { surface: 'app', componentId: 'primary-planning-cta', routePath: '/setup' },
        },
      ])
    );
  });

  it('has no targeted axe violations in the guided planning MVP section', async () => {
    const { container } = render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    const results = await axe(container.querySelector('[data-testid="guided-planning-preview"]') as HTMLElement);

    expect(results).toHaveNoViolations();
  });

  it('redirects protected planning CTAs when session key is missing', async () => {
    const user = userEvent.setup();

    const firstRender = renderHomeRoutes();
    await user.click(screen.getByRole('link', { name: /Continue into the plate flow/i }));
    expect(screen.getByTestId('enter-key-probe')).toHaveTextContent('/plate');
    firstRender.unmount();

    renderHomeRoutes();
    await user.click(screen.getByRole('link', { name: /Use progress check-ins/i }));
    expect(screen.getByTestId('enter-key-probe')).toHaveTextContent('/progress');
  });

  it('opens protected planning CTAs when secure session exists', async () => {
    vi.mocked(useAuth).mockReturnValue({
      apiKey: null,
      isAuthenticated: true,
      isLoading: false,
      setApiKey: vi.fn(),
      clearApiKey: vi.fn(),
      showAuthPrompt: false,
      setShowAuthPrompt: vi.fn(),
    });
    const user = userEvent.setup();

    const firstRender = renderHomeRoutes();
    await user.click(screen.getByRole('link', { name: /Continue into the plate flow/i }));
    expect(screen.getByTestId('plate-route')).toBeInTheDocument();
    firstRender.unmount();

    renderHomeRoutes();
    await user.click(screen.getByRole('link', { name: /Use progress check-ins/i }));
    expect(screen.getByTestId('progress-route')).toBeInTheDocument();
  });

  it('keeps the page token-backed and tabbar-compatible', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    const main = screen.getByRole('main');
    expect(main).toHaveClass('min-h-screen');
    expect(main).toHaveClass('bg-[var(--pp-navy)]');
  });
});

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

function rerenderHomeWithAuthState(
  renderedHome: ReturnType<typeof render>,
  authState: { isAuthenticated: boolean; isLoading: boolean }
): void {
  vi.mocked(useAuth).mockReturnValue({
    apiKey: null,
    isAuthenticated: authState.isAuthenticated,
    isLoading: authState.isLoading,
    setApiKey: vi.fn(),
    clearApiKey: vi.fn(),
    showAuthPrompt: false,
    setShowAuthPrompt: vi.fn(),
  });
  renderedHome.rerender(
    <MemoryRouter>
      <Home />
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
    const guidedPlanningContainer = screen.getByTestId('guided-planning-preview');
    expect(guidedPlanningContainer).toBeInTheDocument();
    expect(screen.getByTestId('mvp-accessibility-evidence')).toHaveTextContent(/selector groups/i);
    expect(screen.getByTestId('mvp-observability-evidence')).toHaveTextContent(/frontend-only interaction evidence/i);
    expect(guidedPlanningContainer.getAttribute('aria-describedby')?.split(' ')).toEqual(
      expect.arrayContaining(['mvp-accessibility-evidence', 'mvp-observability-evidence'])
    );
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
    expect(screen.getByTestId('planning-save-cta')).toBeInTheDocument();
    expect(screen.getByTestId('planning-continue-cta')).toBeInTheDocument();
    expect(screen.getByTestId('planning-progress-state')).toBeInTheDocument();
    expect(screen.getByTestId('planning-save-auth-prompt')).toBeInTheDocument();
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
      'planning_progress_state_viewed',
      'planning_save_prompt_viewed',
      'planning_auth_prompt_viewed',
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
        {
          name: 'planning_progress_state_viewed',
          payload: {
            surface: 'app',
            componentId: 'planning-progress-state',
            routePath: '/app',
            optionId: 'preview_ready',
            authState: 'unauthenticated',
          },
        },
        {
          name: 'planning_auth_prompt_viewed',
          payload: {
            surface: 'app',
            componentId: 'planning-save-auth-prompt',
            routePath: '/app',
            authState: 'unauthenticated',
          },
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
    await user.click(screen.getByTestId('planning-save-cta'));
    await user.click(screen.getByTestId('planning-continue-cta'));
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

  it('shows an honest unauthenticated session-local save and continuation state', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    expect(screen.getByTestId('planning-save-auth-prompt')).toHaveTextContent(
      'Without sign-in, PulsePlate can only mark this preview on this screen.'
    );
    expect(screen.getByTestId('planning-progress-state')).toHaveTextContent(
      'Planning progress starts with your selected intent and practical cooking window.'
    );
    expect(screen.getByTestId('planning-progress-state')).toHaveAttribute('role', 'status');
    expect(screen.getByTestId('planning-save-cta')).toHaveAccessibleName('Mark preview here');
    expect(screen.getByTestId('planning-continue-cta')).toHaveAttribute('href', '/plate');

    await user.click(screen.getByTestId('planning-save-cta'));

    expect(screen.getByTestId('planning-save-cta')).toHaveAccessibleName('Preview marked here');
    expect(screen.getByTestId('planning-progress-state')).toHaveTextContent(
      'Preview marked here. Continue when you are ready to turn this direction into weekly planning.'
    );
    expect(guidedPlanningEvents).toEqual(
      expect.arrayContaining([
        {
          name: 'planning_save_clicked',
          payload: {
            surface: 'app',
            componentId: 'planning-save-cta',
            routePath: '/app',
            optionId: 'consistent',
            authState: 'unauthenticated',
          },
        },
        {
          name: 'planning_progress_state_viewed',
          payload: {
            surface: 'app',
            componentId: 'planning-progress-state',
            routePath: '/app',
            optionId: 'screen_preview_marked',
            authState: 'unauthenticated',
          },
        },
      ])
    );
  });

  it('clears the screen-local preview mark when selections change', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    await user.click(screen.getByTestId('planning-save-cta'));
    expect(screen.getByTestId('planning-save-cta')).toHaveAccessibleName('Preview marked here');

    await user.click(screen.getByRole('button', { name: /Shopping-list planning/i }));

    expect(screen.getByTestId('planning-save-cta')).toHaveAccessibleName('Mark preview here');
    expect(screen.getByTestId('planning-progress-state')).toHaveTextContent(
      'Planning progress starts with your selected intent and practical cooking window.'
    );

    await user.click(screen.getByTestId('planning-save-cta'));
    expect(screen.getByTestId('planning-save-cta')).toHaveAccessibleName('Preview marked here');

    await user.click(screen.getByRole('button', { name: /Batch prep/i }));

    expect(screen.getByTestId('planning-save-cta')).toHaveAccessibleName('Mark preview here');
  });

  it('keeps the screen-local preview mark when the selected option is clicked again', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    await user.click(screen.getByTestId('planning-save-cta'));
    expect(screen.getByTestId('planning-save-cta')).toHaveAccessibleName('Preview marked here');

    await user.click(screen.getByRole('button', { name: /More consistent meals/i }));
    await user.click(screen.getByRole('button', { name: /Standard meal window/i }));

    expect(screen.getByTestId('planning-save-cta')).toHaveAccessibleName('Preview marked here');
  });

  it('does not re-emit prompt viewed events when only planning selections change', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    const initialPromptViews = guidedPlanningEvents.filter(
      (event) => event.name === 'planning_save_prompt_viewed' || event.name === 'planning_auth_prompt_viewed'
    );
    expect(initialPromptViews).toHaveLength(2);

    await user.click(screen.getByRole('button', { name: /Shopping-list planning/i }));
    await user.click(screen.getByRole('button', { name: /Batch prep/i }));

    const promptViewsAfterSelection = guidedPlanningEvents.filter(
      (event) => event.name === 'planning_save_prompt_viewed' || event.name === 'planning_auth_prompt_viewed'
    );
    expect(promptViewsAfterSelection).toHaveLength(2);
  });

  it('emits unauthenticated prompt viewed events once per page view across auth transitions', () => {
    vi.mocked(useAuth).mockReturnValue({
      apiKey: null,
      isAuthenticated: false,
      isLoading: true,
      setApiKey: vi.fn(),
      clearApiKey: vi.fn(),
      showAuthPrompt: false,
      setShowAuthPrompt: vi.fn(),
    });
    const renderedHome = render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    expect(
      guidedPlanningEvents.filter(
        (event) => event.name === 'planning_save_prompt_viewed' || event.name === 'planning_auth_prompt_viewed'
      )
    ).toHaveLength(0);

    rerenderHomeWithAuthState(renderedHome, { isAuthenticated: false, isLoading: false });
    rerenderHomeWithAuthState(renderedHome, { isAuthenticated: false, isLoading: true });
    rerenderHomeWithAuthState(renderedHome, { isAuthenticated: false, isLoading: false });

    const promptViewsAfterAuthTransitions = guidedPlanningEvents.filter(
      (event) => event.name === 'planning_save_prompt_viewed' || event.name === 'planning_auth_prompt_viewed'
    );
    expect(promptViewsAfterAuthTransitions).toHaveLength(2);
  });

  it('uses neutral save copy while auth state is loading', () => {
    vi.mocked(useAuth).mockReturnValue({
      apiKey: null,
      isAuthenticated: false,
      isLoading: true,
      setApiKey: vi.fn(),
      clearApiKey: vi.fn(),
      showAuthPrompt: false,
      setShowAuthPrompt: vi.fn(),
    });
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    expect(screen.getByTestId('planning-progress-state')).toHaveTextContent(
      'Checking your session before PulsePlate routes this preview into protected planning flows.'
    );
    expect(screen.getByTestId('planning-save-auth-prompt')).toHaveTextContent('Checking session');
    expect(screen.queryByText(/Without sign-in/i)).not.toBeInTheDocument();
    expect(guidedPlanningEvents).toEqual(
      expect.arrayContaining([
        {
          name: 'planning_progress_state_viewed',
          payload: {
            surface: 'app',
            componentId: 'planning-progress-state',
            routePath: '/app',
            optionId: 'preview_ready',
            authState: 'unknown',
          },
        },
      ])
    );
  });

  it('shows authenticated save-ready copy without claiming backend persistence', async () => {
    const user = userEvent.setup();
    vi.mocked(useAuth).mockReturnValue({
      apiKey: null,
      isAuthenticated: true,
      isLoading: false,
      setApiKey: vi.fn(),
      clearApiKey: vi.fn(),
      showAuthPrompt: false,
      setShowAuthPrompt: vi.fn(),
    });
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    expect(screen.getByTestId('planning-save-auth-prompt')).toHaveTextContent('Your planning direction is ready');
    expect(screen.getByTestId('planning-save-auth-prompt')).toHaveTextContent('on this screen');
    expect(screen.getByTestId('planning-save-cta')).toHaveAccessibleName('Mark preview ready here');

    await user.click(screen.getByTestId('planning-save-cta'));

    expect(screen.queryByText(/saved to your account/i)).not.toBeInTheDocument();
    expect(screen.getByTestId('planning-save-auth-prompt')).not.toHaveTextContent(/saved weekly plan/i);
    expect(screen.queryByText(/for the current session/i)).not.toBeInTheDocument();
    expect(guidedPlanningEvents).toEqual(
      expect.arrayContaining([
        {
          name: 'planning_save_clicked',
          payload: {
            surface: 'app',
            componentId: 'planning-save-cta',
            routePath: '/app',
            optionId: 'consistent',
            authState: 'authenticated',
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
    expect(screen.getByTestId('planning-continue-cta')).toHaveAttribute('href', '/plate');
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

    const guidedPlanningSection = container.querySelector('[data-testid="guided-planning-preview"]');
    if (!(guidedPlanningSection instanceof HTMLElement)) {
      throw new Error('Guided planning preview section not found');
    }
    const results = await axe(guidedPlanningSection);

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

  it('emits continue evidence before protected route redirects', async () => {
    const user = userEvent.setup();

    renderHomeRoutes();
    await user.click(screen.getByTestId('planning-continue-cta'));

    expect(screen.getByTestId('enter-key-probe')).toHaveTextContent('/plate');
    expect(guidedPlanningEvents).toEqual(
      expect.arrayContaining([
        {
          name: 'planning_continue_clicked',
          payload: {
            surface: 'app',
            componentId: 'planning-continue-cta',
            routePath: '/plate',
            optionId: 'standard',
            authState: 'unauthenticated',
          },
        },
      ])
    );
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

  it('emits authenticated continuation evidence for protected and upgrade routes', async () => {
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

    const plateRender = renderHomeRoutes();
    await user.click(screen.getByTestId('planning-continue-cta'));
    expect(screen.getByTestId('plate-route')).toBeInTheDocument();
    plateRender.unmount();

    const progressRender = renderHomeRoutes();
    await user.click(screen.getByRole('link', { name: /Use progress check-ins/i }));
    expect(screen.getByTestId('progress-route')).toBeInTheDocument();
    progressRender.unmount();

    renderHomeRoutes();
    await user.click(screen.getByRole('link', { name: /Unlock weekly planning/i }));
    expect(screen.getByTestId('pro-route')).toBeInTheDocument();

    expect(guidedPlanningEvents).toEqual(
      expect.arrayContaining([
        {
          name: 'planning_continue_clicked',
          payload: {
            surface: 'app',
            componentId: 'planning-continue-cta',
            routePath: '/plate',
            optionId: 'standard',
            authState: 'authenticated',
          },
        },
        {
          name: 'planning_continue_clicked',
          payload: {
            surface: 'app',
            componentId: 'planning-continue-cta',
            routePath: '/progress',
            optionId: 'standard',
            authState: 'authenticated',
          },
        },
        {
          name: 'planning_continue_clicked',
          payload: {
            surface: 'app',
            componentId: 'planning-continue-cta',
            routePath: '/pro',
            optionId: 'standard',
            authState: 'authenticated',
          },
        },
      ])
    );
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

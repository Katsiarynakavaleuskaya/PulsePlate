import { JSX } from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import Home from '../Home';
import { RequireKey } from '../../auth/RequireKey';
import { routes, type RoutePath } from '../../config/routes';

vi.mock('../../lib/auth', () => ({
  useAuth: vi.fn(),
}));

vi.mock('../../lib/usePremium', () => ({
  usePremium: vi.fn(),
}));

vi.mock('../../api/premium', async () => {
  const actual = await vi.importActual<typeof import('../../api/premium')>('../../api/premium');
  return {
    ...actual,
    getCbtInsight: vi.fn(),
  };
});

import { useAuth } from '../../lib/auth';
import { usePremium } from '../../lib/usePremium';
import { getCbtInsight } from '../../api/premium';

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
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={renderConfiguredRoute('/', <Home />)} />
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
        <Route path="/enter-key" element={renderConfiguredRoute('/enter-key', <EnterKeyProbe />)} />
      </Routes>
    </MemoryRouter>
  );
}

describe('Home', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      apiKey: null,
      isAuthenticated: false,
      isLoading: false,
      setApiKey: vi.fn(),
      clearApiKey: vi.fn(),
      showAuthPrompt: false,
      setShowAuthPrompt: vi.fn(),
    });
    vi.mocked(usePremium).mockReturnValue(false);
    vi.mocked(getCbtInsight).mockReset();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('renders home page content', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: 'Home' })).toBeInTheDocument();
    expect(screen.getByLabelText('Live progress indicator')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'View detailed progress' })).toHaveAttribute('href', '/progress');
    expect(screen.getByText('Quick Navigation')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Configure Setup' })).toHaveAttribute('href', '/setup');
    expect(screen.getByRole('link', { name: 'Nutrition Plate' })).toHaveAttribute('href', '/plate');
    expect(screen.getByRole('link', { name: 'Progress View' })).toHaveAttribute('href', '/progress');
    expect(screen.getByRole('link', { name: 'Premium Features' })).toHaveAttribute('href', '/pro');
  });

  it('shows connected API status from authenticated session', () => {
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

    expect(screen.getByText('Connected')).toBeInTheDocument();
    expect(
      screen.getByText('Your secure session is active. Personalized guidance is enabled.')
    ).toBeInTheDocument();
  });

  it('shows AI session CTA when user is not authenticated', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { level: 2, name: 'AI Insight' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Connect secure session' })).toHaveAttribute('href', '/enter-key');
  });

  it('shows upgrade CTA for authenticated non-premium users', () => {
    vi.mocked(useAuth).mockReturnValue({
      apiKey: 'present', // pragma: allowlist secret -- test auth sentinel / тестовый маркер авторизации
      isAuthenticated: true,
      isLoading: false,
      setApiKey: vi.fn(),
      clearApiKey: vi.fn(),
      showAuthPrompt: false,
      setShowAuthPrompt: vi.fn(),
    });
    vi.mocked(usePremium).mockReturnValue(false);

    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    expect(screen.getByRole('link', { name: 'Upgrade to Pro' })).toHaveAttribute('href', '/pro');
    expect(screen.queryByRole('button', { name: 'Generate insight' })).not.toBeInTheDocument();
  });

  it('lets premium users submit AI query and renders reliability metadata', async () => {
    vi.mocked(useAuth).mockReturnValue({
      apiKey: 'present', // pragma: allowlist secret -- test auth sentinel / тестовый маркер авторизации
      isAuthenticated: true,
      isLoading: false,
      setApiKey: vi.fn(),
      clearApiKey: vi.fn(),
      showAuthPrompt: false,
      setShowAuthPrompt: vi.fn(),
    });
    vi.mocked(usePremium).mockReturnValue(true);
    vi.mocked(getCbtInsight).mockResolvedValue({
      insight: 'Focus on consistent protein intake and simpler meal repetition.',
      confidence: 0.93,
      uncertainty: 0.07,
      rag_used: true,
      sources: [
        {
          chunk_id: 'chunk-1',
          file: 'docs/cbt/foundation.md',
          preview: 'Track the trigger before rewriting the pattern.',
          score: 0.98,
        },
      ],
      warnings: ['Monitor stress-linked snacking patterns.'],
      mode: 'auto-safe',
      quota_state: 'consumed',
    });
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    await user.type(screen.getByLabelText('Ask one question'), 'What should I focus on this week?');
    await user.click(screen.getByRole('button', { name: 'Generate insight' }));

    expect(vi.mocked(getCbtInsight)).toHaveBeenCalledWith({ query: 'What should I focus on this week?' });
    expect(screen.getByText('Focus on consistent protein intake and simpler meal repetition.')).toBeInTheDocument();
    expect(screen.getByText('Mode: auto-safe')).toBeInTheDocument();
    expect(screen.getByText('Quota: consumed')).toBeInTheDocument();
    expect(screen.getByText('RAG: Used')).toBeInTheDocument();
    expect(screen.getByText('Confidence: 0.93')).toBeInTheDocument();
    expect(screen.getByText('Uncertainty: 0.07')).toBeInTheDocument();
    expect(screen.getByText('Monitor stress-linked snacking patterns.')).toBeInTheDocument();
    expect(screen.getByText('foundation.md: Track the trigger before rewriting the pattern.')).toBeInTheDocument();
  });

  it('renders friendly AI error state without breaking existing CTAs', async () => {
    vi.mocked(useAuth).mockReturnValue({
      apiKey: 'present', // pragma: allowlist secret -- test auth sentinel / тестовый маркер авторизации
      isAuthenticated: true,
      isLoading: false,
      setApiKey: vi.fn(),
      clearApiKey: vi.fn(),
      showAuthPrompt: false,
      setShowAuthPrompt: vi.fn(),
    });
    vi.mocked(usePremium).mockReturnValue(true);
    vi.mocked(getCbtInsight).mockRejectedValue(new Error('Unable to load AI insight right now.'));
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    await user.type(screen.getByLabelText('Ask one question'), 'Need a quick summary');
    await user.click(screen.getByRole('button', { name: 'Generate insight' }));

    expect(screen.getByRole('alert')).toHaveTextContent('Unable to load AI insight right now.');
    expect(screen.getByRole('link', { name: 'Nutrition Plate' })).toHaveAttribute('href', '/plate');
  });

  it('has correct CSS classes', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    const main = screen.getByRole('main');
    expect(main).toHaveClass('flex');
    expect(main).toHaveClass('min-h-screen');
    expect(main).toHaveClass('flex-col');
  });

  it('navigates to setup flow from the primary CTA', async () => {
    const user = userEvent.setup();

    renderHomeRoutes();

    await user.click(screen.getByRole('link', { name: 'Configure Setup' }));

    expect(screen.getByTestId('setup-route')).toBeInTheDocument();
    expect(screen.queryByTestId('enter-key-probe')).not.toBeInTheDocument();
  });

  it('redirects Home auth-gated CTAs to enter-key when session key is missing', async () => {
    const user = userEvent.setup();

    const firstRender = renderHomeRoutes();
    await user.click(screen.getByRole('link', { name: 'Nutrition Plate' }));
    expect(screen.getByTestId('enter-key-probe')).toHaveTextContent('/plate');
    firstRender.unmount();

    renderHomeRoutes();
    await user.click(screen.getByRole('link', { name: 'Progress View' }));
    expect(screen.getByTestId('enter-key-probe')).toHaveTextContent('/progress');
  });

  it('opens Home auth-gated CTAs when session key exists', async () => {
    vi.mocked(useAuth).mockReturnValue({
      apiKey: 'present', // pragma: allowlist secret -- test auth sentinel / тестовый маркер авторизации
      isAuthenticated: true,
      isLoading: false,
      setApiKey: vi.fn(),
      clearApiKey: vi.fn(),
      showAuthPrompt: false,
      setShowAuthPrompt: vi.fn(),
    });
    const user = userEvent.setup();

    const firstRender = renderHomeRoutes();
    await user.click(screen.getByRole('link', { name: 'Nutrition Plate' }));
    expect(screen.getByTestId('plate-route')).toBeInTheDocument();
    firstRender.unmount();

    renderHomeRoutes();
    await user.click(screen.getByRole('link', { name: 'Progress View' }));
    expect(screen.getByTestId('progress-route')).toBeInTheDocument();
  });
});

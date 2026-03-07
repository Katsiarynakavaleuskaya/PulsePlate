import { JSX } from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import Home from '../Home';
import { RequireKey } from '../../auth/RequireKey';

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

function renderHomeRoutes(): ReturnType<typeof render> {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/setup" element={<div data-testid="setup-route">Nutrition Setup Flow</div>} />
        <Route
          path="/plate"
          element={
            <RequireKey>
              <div data-testid="plate-route">Plate route</div>
            </RequireKey>
          }
        />
        <Route
          path="/progress"
          element={
            <RequireKey>
              <div data-testid="progress-route">Progress route</div>
            </RequireKey>
          }
        />
        <Route path="/enter-key" element={<EnterKeyProbe />} />
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

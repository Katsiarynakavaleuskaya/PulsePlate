/* @vitest-environment jsdom */
import type { JSX, ReactNode } from 'react';
import '@testing-library/jest-dom/vitest';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import Plate from '../Plate';
import { PREMIUM_GATE_SOURCES } from '../../config/constants';
import '../../test/setup';

// Mock usePremium hook
vi.mock('../../lib/usePremium', () => ({
  usePremium: vi.fn()
}));

// Mock PremiumGate component
vi.mock('../../components/PremiumGate', () => {
  const premiumGatePropsSpy = vi.fn();

  return {
    premiumGatePropsSpy,
    default: ({
      children,
      isPremium,
      source,
      paywallSource,
      triggerReason,
    }: {
      children: ReactNode;
      isPremium: boolean;
      source: string;
      paywallSource?: string;
      triggerReason?: string;
    }): JSX.Element => {
      premiumGatePropsSpy({ isPremium, source, paywallSource, triggerReason });

      return isPremium ? (
        <div
          data-testid="premium-gate"
          data-premium={String(isPremium)}
          data-source={source}
          data-paywall-source={paywallSource ?? ''}
          data-trigger-reason={triggerReason ?? ''}
        >
          {children}
        </div>
      ) : (
        <div
          data-testid="premium-gate-locked"
          data-premium={String(isPremium)}
          data-source={source}
          data-paywall-source={paywallSource ?? ''}
          data-trigger-reason={triggerReason ?? ''}
        >
          <div
            data-testid="premium-gate-preview"
            aria-hidden="true"
            className="opacity-60 pointer-events-none"
          >
            {children}
          </div>
          <button type="button">Continue</button>
        </div>
      );
    }
  };
});

import { usePremium } from '../../lib/usePremium';
import { premiumGatePropsSpy } from '../../components/PremiumGate';

function renderPlateRoutes(routeState?: { triggerReason?: string }): ReturnType<typeof render> {
  return render(
    <MemoryRouter initialEntries={[{ pathname: '/plate', state: routeState }]}>
      <Routes>
        <Route path="/plate" element={<Plate />} />
        <Route path="/setup" element={<div data-testid="setup-route">Setup route</div>} />
        <Route path="/progress" element={<div data-testid="progress-route">Progress route</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe('Plate', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('renders loading state when premium status is undefined', () => {
    vi.mocked(usePremium).mockReturnValue(undefined);

    render(
      <MemoryRouter>
        <Plate />
      </MemoryRouter>
    );

    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: 'Plate' })).toBeInTheDocument();
    expect(screen.getByText('Loading your nutrition data…')).toBeInTheDocument();
  });

  it('renders premium gate when premium status is defined', () => {
    vi.mocked(usePremium).mockReturnValue(true);

    render(
      <MemoryRouter>
        <Plate />
      </MemoryRouter>
    );

    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: 'Your Plate' })).toBeInTheDocument();
    expect(screen.getByTestId('premium-gate')).toBeInTheDocument();
    expect(screen.getByText('Premium Nutrition Controls')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Configure Setup' })).toHaveAttribute('href', '/setup');
    expect(screen.getByLabelText('Live progress indicator')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'View detailed progress' })).toHaveAttribute('href', '/progress');
  });

  it('passes correct isPremium prop to PremiumGate', () => {
    vi.mocked(usePremium).mockReturnValue(false);

    render(
      <MemoryRouter>
        <Plate />
      </MemoryRouter>
    );

    const premiumGate = screen.getByTestId('premium-gate-locked');
    const preview = screen.getByTestId('premium-gate-preview');
    expect(premiumGate).toHaveAttribute('data-premium', 'false');
    expect(preview).toHaveAttribute('aria-hidden', 'true');
    expect(preview).toHaveClass('pointer-events-none');
    expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Configure Setup', hidden: true })).toHaveAttribute(
      'href',
      '/setup'
    );
    expect(screen.getByRole('link', { name: 'View Progress', hidden: true })).toHaveAttribute(
      'href',
      '/progress'
    );
  });

  it('has correct CSS classes', () => {
    vi.mocked(usePremium).mockReturnValue(true);

    render(
      <MemoryRouter>
        <Plate />
      </MemoryRouter>
    );

    const main = screen.getByRole('main');
    expect(main).toHaveClass('flex');
    expect(main).toHaveClass('min-h-screen');
    expect(main).toHaveClass('flex-col');
  });

  it('passes correct source prop to PremiumGate', () => {
    vi.mocked(usePremium).mockReturnValue(true);

    render(
      <MemoryRouter>
        <Plate />
      </MemoryRouter>
    );

    const premiumGate = screen.getByTestId('premium-gate');
    expect(premiumGate).toHaveAttribute('data-source', PREMIUM_GATE_SOURCES.PLATE_PAGE);
    expect(premiumGate).toHaveAttribute('data-paywall-source', PREMIUM_GATE_SOURCES.PRO_DAILY_PLATE);
    expect(premiumGate).toHaveAttribute('data-trigger-reason', '');
    expect(premiumGatePropsSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        source: PREMIUM_GATE_SOURCES.PLATE_PAGE,
        paywallSource: PREMIUM_GATE_SOURCES.PRO_DAILY_PLATE,
        triggerReason: undefined,
      })
    );
  });

  it('routes premium Plate CTAs to setup and progress screens', async () => {
    vi.mocked(usePremium).mockReturnValue(true);
    const user = userEvent.setup();

    const firstRender = renderPlateRoutes();
    await user.click(screen.getByRole('link', { name: 'Configure Setup' }));
    expect(screen.getByTestId('setup-route')).toBeInTheDocument();
    firstRender.unmount();

    renderPlateRoutes();
    await user.click(screen.getByRole('link', { name: 'View Progress' }));
    expect(screen.getByTestId('progress-route')).toBeInTheDocument();
  });

  it('forwards planning trigger reason only when the route provides it', () => {
    vi.mocked(usePremium).mockReturnValue(true);

    renderPlateRoutes({ triggerReason: 'targets_ready' });

    const premiumGate = screen.getByTestId('premium-gate');
    expect(premiumGate).toHaveAttribute('data-trigger-reason', 'targets_ready');
    expect(premiumGatePropsSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        source: PREMIUM_GATE_SOURCES.PLATE_PAGE,
        paywallSource: PREMIUM_GATE_SOURCES.PRO_DAILY_PLATE,
        triggerReason: 'targets_ready',
      })
    );
  });
});

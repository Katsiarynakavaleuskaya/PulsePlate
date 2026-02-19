import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Plate from '../Plate';
import { PREMIUM_GATE_SOURCES } from '../../config/constants';

// Mock usePremium hook
vi.mock('../../lib/usePremium', () => ({
  usePremium: vi.fn()
}));

// Mock PremiumGate component
vi.mock('../../components/PremiumGate', () => ({
  default: ({ children, isPremium, source }: { children: React.ReactNode; isPremium: boolean; source: string }) => (
    <div data-testid="premium-gate" data-premium={isPremium} data-source={source}>
      {children}
    </div>
  )
}));

import { usePremium } from '../../lib/usePremium';

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
    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });

  it('renders premium gate when premium status is defined', () => {
    vi.mocked(usePremium).mockReturnValue(true);

    render(
      <MemoryRouter>
        <Plate />
      </MemoryRouter>
    );

    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: 'Plate' })).toBeInTheDocument();
    expect(screen.getByTestId('premium-gate')).toBeInTheDocument();
    expect(screen.getByText('PRO nutrition controls')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open setup' })).toBeInTheDocument();
    expect(screen.getByLabelText('Live progress indicator')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open progress live' })).toHaveAttribute('href', '/progress');
  });

  it('passes correct isPremium prop to PremiumGate', () => {
    vi.mocked(usePremium).mockReturnValue(false);

    render(
      <MemoryRouter>
        <Plate />
      </MemoryRouter>
    );

    const premiumGate = screen.getByTestId('premium-gate');
    expect(premiumGate).toHaveAttribute('data-premium', 'false');
  });

  it('has correct CSS classes', () => {
    vi.mocked(usePremium).mockReturnValue(true);

    render(
      <MemoryRouter>
        <Plate />
      </MemoryRouter>
    );

    const main = screen.getByRole('main');
    expect(main).toHaveClass('p-4');
    expect(main).toHaveClass('pb-24');
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
  });
});

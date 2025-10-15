import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import Plate from '../Plate';

// Mock usePremium hook
vi.mock('../../lib/usePremium', () => ({
  usePremium: vi.fn()
}));

// Mock PremiumGate component
vi.mock('../../components/PremiumGate', () => ({
  default: ({ children, isPremium }: { children: React.ReactNode; isPremium: boolean }) => (
    <div data-testid="premium-gate" data-premium={isPremium}>
      {children}
    </div>
  )
}));

import { usePremium } from '../../lib/usePremium';

describe('Plate', () => {
  it('renders loading state when premium status is undefined', () => {
    vi.mocked(usePremium).mockReturnValue(undefined);

    render(<Plate />);

    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByText('Plate')).toBeInTheDocument();
    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });

  it('renders premium gate when premium status is defined', () => {
    vi.mocked(usePremium).mockReturnValue(true);

    render(<Plate />);

    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByText('Plate')).toBeInTheDocument();
    expect(screen.getByTestId('premium-gate')).toBeInTheDocument();
    expect(screen.getByText('Premium-only section preview…')).toBeInTheDocument();
  });

  it('passes correct props to PremiumGate', () => {
    vi.mocked(usePremium).mockReturnValue(false);

    render(<Plate />);

    const premiumGate = screen.getByTestId('premium-gate');
    expect(premiumGate).toHaveAttribute('data-premium', 'false');
  });

  it('has correct CSS classes', () => {
    vi.mocked(usePremium).mockReturnValue(true);

    render(<Plate />);

    const main = screen.getByRole('main');
    expect(main).toHaveClass('p-4');
  });
});

/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import {
  VipFeature,
  VipBadge,
  VipGate,
  VipPageHeader,
  VipFeatureCard,
  VipSection
} from '../VipFeature';

// Mock useVipModule hook
const mockUseVipModule = vi.fn();
vi.mock('../../lib/useFeatureFlag', () => ({
  useVipModule: () => mockUseVipModule(),
}));

// Mock useTranslation
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock Paywall component
vi.mock('../Paywall/BeforeAfter', () => ({
  default: ({ onClose, onPurchase }: { onClose: () => void; onPurchase: () => void }) => (
    <div data-testid="paywall">
      <button onClick={onClose}>Close</button>
      <button onClick={onPurchase}>Purchase</button>
    </div>
  ),
}));

describe('VipFeature', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe('VipFeature wrapper', () => {
    it('should render children when VIP is enabled', () => {
      mockUseVipModule.mockReturnValue(true);

      render(
        <VipFeature>
          <div data-testid="vip-content">VIP Content</div>
        </VipFeature>
      );

      expect(screen.getByTestId('vip-content')).toBeInTheDocument();
    });

    it('should render fallback when VIP is disabled', () => {
      mockUseVipModule.mockReturnValue(false);

      render(
        <VipFeature fallback={<div data-testid="fallback">Fallback Content</div>}>
          <div data-testid="vip-content">VIP Content</div>
        </VipFeature>
      );

      expect(screen.getByTestId('fallback')).toBeInTheDocument();
      expect(screen.queryByTestId('vip-content')).not.toBeInTheDocument();
    });

    it('should render nothing when VIP is disabled and no fallback provided', () => {
      mockUseVipModule.mockReturnValue(false);

      const { container } = render(
        <VipFeature>
          <div data-testid="vip-content">VIP Content</div>
        </VipFeature>
      );

      expect(container.firstChild).toBeNull();
    });
  });

  describe('VipBadge', () => {
    it('should render VIP badge when VIP is enabled', () => {
      mockUseVipModule.mockReturnValue(true);

      render(<VipBadge />);

      expect(screen.getByText('vip.badge')).toBeInTheDocument();
    });

    it('should not render when VIP is disabled', () => {
      mockUseVipModule.mockReturnValue(false);

      const { container } = render(<VipBadge />);

      expect(container.firstChild).toBeNull();
    });
  });

  describe('VipGate', () => {
    it('should render children when VIP is enabled', () => {
      render(
        <VipGate isVip={true}>
          <div data-testid="vip-content">VIP Content</div>
        </VipGate>
      );

      expect(screen.getByTestId('vip-content')).toBeInTheDocument();
    });

    it('should render gate when VIP is disabled', () => {
      render(
        <VipGate isVip={false}>
          <div data-testid="vip-content">VIP Content</div>
        </VipGate>
      );

      expect(screen.getByTestId('vip-content')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /vip.cta/i })).toBeInTheDocument();
    });

    it('should render legacy gate UI when no children provided', () => {
      render(<VipGate />);

      expect(screen.getByText('VIP Feature')).toBeInTheDocument();
      expect(screen.getByText('vip.subtitle')).toBeInTheDocument();
      expect(screen.getByText('vip.cta')).toBeInTheDocument();
    });

    it('should render legacy gate UI with custom message', () => {
      const customMessage = 'Custom VIP message';
      render(<VipGate message={customMessage} />);

      expect(screen.getByText('VIP Feature')).toBeInTheDocument();
      expect(screen.getByText(customMessage)).toBeInTheDocument();
      expect(screen.getByText('vip.cta')).toBeInTheDocument();
    });

    it('should use useVipModule hook when isVip not provided', () => {
      mockUseVipModule.mockReturnValue(true);

      render(
        <VipGate>
          <div data-testid="vip-content">VIP Content</div>
        </VipGate>
      );

      expect(screen.getByTestId('vip-content')).toBeInTheDocument();
    });

    it('opens paywall on CTA click', () => {
      render(
        <VipGate isVip={false}>
          <div>Preview</div>
        </VipGate>
      );

      fireEvent.click(screen.getByRole('button', { name: /vip\.cta/i }));
      expect(screen.getByTestId('paywall')).toBeInTheDocument();
    });
  });

  describe('VipBadge variants', () => {
    it('should render with different sizes', () => {
      mockUseVipModule.mockReturnValue(true);

      const { rerender } = render(<VipBadge size="sm" />);
      expect(screen.getByText('vip.badge')).toBeInTheDocument();

      rerender(<VipBadge size="md" />);
      expect(screen.getByText('vip.badge')).toBeInTheDocument();

      rerender(<VipBadge size="lg" />);
      expect(screen.getByText('vip.badge')).toBeInTheDocument();
    });

    it('should render with different variants', () => {
      mockUseVipModule.mockReturnValue(true);

      const { rerender } = render(<VipBadge variant="default" />);
      expect(screen.getByText('vip.badge')).toBeInTheDocument();

      rerender(<VipBadge variant="outline" />);
      expect(screen.getByText('vip.badge')).toBeInTheDocument();

      rerender(<VipBadge variant="subtle" />);
      expect(screen.getByText('vip.badge')).toBeInTheDocument();
    });
  });

  describe('VipPageHeader', () => {
    it('should render title and VIP badge', () => {
      mockUseVipModule.mockReturnValue(true);

      render(<VipPageHeader title="VIP Dashboard" />);

      expect(screen.getByText('VIP Dashboard')).toBeInTheDocument();
      expect(screen.getByText('vip.badge')).toBeInTheDocument();
    });

    it('should render subtitle when provided', () => {
      mockUseVipModule.mockReturnValue(true);

      render(
        <VipPageHeader
          title="VIP Dashboard"
          subtitle="Manage your VIP features"
        />
      );

      expect(screen.getByText('VIP Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Manage your VIP features')).toBeInTheDocument();
    });
  });

  describe('VipFeatureCard', () => {
    it('should render card with title and description', () => {
      render(
        <VipFeatureCard
          title="Advanced Analytics"
          description="Get detailed insights into your nutrition"
        />
      );

      expect(screen.getByText('Advanced Analytics')).toBeInTheDocument();
      expect(screen.getByText('Get detailed insights into your nutrition')).toBeInTheDocument();
    });

    it('should render with icon when provided', () => {
      const icon = <span data-testid="icon">📊</span>;

      render(
        <VipFeatureCard
          title="Advanced Analytics"
          description="Get detailed insights"
          icon={icon}
        />
      );

      expect(screen.getByTestId('icon')).toBeInTheDocument();
    });

    it('should render children inside VipFeatureCard', () => {
      render(
        <VipFeatureCard
          title="Child Test"
          description="Testing children"
        >
          <div data-testid="vip-feature-child">Child Content</div>
        </VipFeatureCard>
      );

      expect(screen.getByTestId('vip-feature-child')).toBeInTheDocument();
      expect(screen.getByText('Child Content')).toBeInTheDocument();
    });
  });

  describe('VipSection', () => {
    it('should render section with title and children', () => {
      render(
        <VipSection title="VIP Features">
          <div data-testid="section-content">Section content</div>
        </VipSection>
      );

      expect(screen.getByText('VIP Features')).toBeInTheDocument();
      expect(screen.getByTestId('section-content')).toBeInTheDocument();
    });
  });
});

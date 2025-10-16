/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
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

      expect(screen.getByText('VIP')).toBeInTheDocument();
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
  });

  describe('VipBadge variants', () => {
    it('should render with different sizes', () => {
      mockUseVipModule.mockReturnValue(true);

      const { rerender } = render(<VipBadge size="sm" />);
      expect(screen.getByText('VIP')).toBeInTheDocument();

      rerender(<VipBadge size="md" />);
      expect(screen.getByText('VIP')).toBeInTheDocument();

      rerender(<VipBadge size="lg" />);
      expect(screen.getByText('VIP')).toBeInTheDocument();
    });

    it('should render with different variants', () => {
      mockUseVipModule.mockReturnValue(true);

      const { rerender } = render(<VipBadge variant="default" />);
      expect(screen.getByText('VIP')).toBeInTheDocument();

      rerender(<VipBadge variant="outline" />);
      expect(screen.getByText('VIP')).toBeInTheDocument();

      rerender(<VipBadge variant="subtle" />);
      expect(screen.getByText('VIP')).toBeInTheDocument();
    });
  });

  describe('VipPageHeader', () => {
    it('should render title and VIP badge', () => {
      mockUseVipModule.mockReturnValue(true);

      render(<VipPageHeader title="VIP Dashboard" />);

      expect(screen.getByText('VIP Dashboard')).toBeInTheDocument();
      expect(screen.getByText('VIP')).toBeInTheDocument();
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

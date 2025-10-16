/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { VipFeature, VipBadge, VipGate } from '../VipFeature';

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
    it('should render VIP gate with default message', () => {
      render(<VipGate />);

      expect(screen.getByText('VIP Feature')).toBeInTheDocument();
      expect(screen.getByText('This feature requires VIP access')).toBeInTheDocument();
      expect(screen.getByText('Upgrade to VIP')).toBeInTheDocument();
    });

    it('should render VIP gate with custom message', () => {
      const customMessage = 'Custom VIP message';

      render(<VipGate message={customMessage} />);

      expect(screen.getByText('VIP Feature')).toBeInTheDocument();
      expect(screen.getByText(customMessage)).toBeInTheDocument();
      expect(screen.getByText('Upgrade to VIP')).toBeInTheDocument();
    });
  });
});

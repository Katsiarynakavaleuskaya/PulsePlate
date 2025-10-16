import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { trackVipEvent, vipTelemetry, isTelemetryEnabled } from '../telemetry';
import { isAnalyticsEnabled } from '../../config/features';

// Mock the analytics module
vi.mock('../analytics', () => ({
  log: vi.fn(),
}));

// Mock the features module
vi.mock('../../config/features', () => ({
  isAnalyticsEnabled: vi.fn(),
}));

describe('Telemetry', () => {
  let mockLog: any;
  const mockIsAnalyticsEnabled = vi.mocked(isAnalyticsEnabled);

  beforeEach(async () => {
    const analyticsModule = await import('../analytics');
    mockLog = vi.mocked(analyticsModule.log);
    vi.clearAllMocks();
    mockIsAnalyticsEnabled.mockReturnValue(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('trackVipEvent', () => {
    it('should track event when analytics is enabled', () => {
      trackVipEvent('vip_module_viewed', {
        source: 'dashboard',
        vipEnabled: true,
      });

      expect(mockLog).toHaveBeenCalledWith('vip_module_viewed', {
        timestamp: expect.any(Number),
        source: 'dashboard',
        vipEnabled: true,
      });
    });

    it('should not track event when analytics is disabled', () => {
      mockIsAnalyticsEnabled.mockReturnValue(false);

      trackVipEvent('vip_module_viewed', {
        source: 'dashboard',
        vipEnabled: true,
      });

      expect(mockLog).not.toHaveBeenCalled();
    });

    it('should add timestamp if not provided', () => {
      const beforeTime = Date.now();

      trackVipEvent('vip_feature_clicked', {
        featureName: 'advanced_analytics',
        source: 'dashboard',
        isVip: false,
      });

      const afterTime = Date.now();
      const callArgs = mockLog.mock.calls[0];
      const payload = callArgs[1] as any;

      expect(payload.timestamp).toBeGreaterThanOrEqual(beforeTime);
      expect(payload.timestamp).toBeLessThanOrEqual(afterTime);
    });

    it('should preserve provided timestamp', () => {
      const customTimestamp = 1234567890;

      trackVipEvent('vip_feature_clicked', {
        featureName: 'advanced_analytics',
        source: 'dashboard',
        isVip: false,
        timestamp: customTimestamp,
      });

      expect(mockLog).toHaveBeenCalledWith('vip_feature_clicked', {
        timestamp: customTimestamp,
        featureName: 'advanced_analytics',
        source: 'dashboard',
        isVip: false,
      });
    });
  });

  describe('vipTelemetry', () => {
    describe('moduleViewed', () => {
      it('should track VIP module view', () => {
        vipTelemetry.moduleViewed('dashboard', true);

        expect(mockLog).toHaveBeenCalledWith('vip_module_viewed', {
          timestamp: expect.any(Number),
          source: 'dashboard',
          vipEnabled: true,
        });
      });
    });

    describe('featureClicked', () => {
      it('should track VIP feature click', () => {
        vipTelemetry.featureClicked('advanced_analytics', 'dashboard', false);

      expect(mockLog).toHaveBeenCalledWith('vip_feature_clicked', {
        timestamp: expect.any(Number),
        featureName: 'advanced_analytics',
        source: 'dashboard',
        isVip: false,
      });
      });
    });

    describe('paywallViewed', () => {
      it('should track paywall view', () => {
        vipTelemetry.paywallViewed('dashboard', 'feature_gate', true);

        expect(mockLog).toHaveBeenCalledWith('vip_paywall_viewed', {
          timestamp: expect.any(Number),
          source: 'dashboard',
          context: 'feature_gate',
          isRetry: true,
        });
      });

      it('should track paywall view without isRetry', () => {
        vipTelemetry.paywallViewed('dashboard', 'feature_gate');

        expect(mockLog).toHaveBeenCalledWith('vip_paywall_viewed', {
          timestamp: expect.any(Number),
          source: 'dashboard',
          context: 'feature_gate',
        });
      });
    });

    describe('paywallDismissed', () => {
      it('should track paywall dismissal', () => {
        vipTelemetry.paywallDismissed('dashboard', 'close_button', 5000);

        expect(mockLog).toHaveBeenCalledWith('vip_paywall_dismissed', {
          timestamp: expect.any(Number),
          source: 'dashboard',
          dismissMethod: 'close_button',
          viewDuration: 5000,
        });
      });

      it('should track paywall dismissal without viewDuration', () => {
        vipTelemetry.paywallDismissed('dashboard', 'backdrop');

        expect(mockLog).toHaveBeenCalledWith('vip_paywall_dismissed', {
          timestamp: expect.any(Number),
          source: 'dashboard',
          dismissMethod: 'backdrop',
        });
      });
    });

    describe('upgradeClicked', () => {
      it('should track upgrade click', () => {
        vipTelemetry.upgradeClicked('dashboard', 'paywall', false);

        expect(mockLog).toHaveBeenCalledWith('vip_upgrade_clicked', {
          timestamp: expect.any(Number),
          source: 'dashboard',
          context: 'paywall',
          isRetry: false,
        });
      });
    });

    describe('gateInteracted', () => {
      it('should track VIP gate interaction', () => {
        vipTelemetry.gateInteracted('advanced_analytics', 'click', true);

        expect(mockLog).toHaveBeenCalledWith('vip_gate_interacted', {
          timestamp: expect.any(Number),
          featureName: 'advanced_analytics',
          interactionType: 'click',
          isVip: true,
        });
      });
    });

    describe('badgeViewed', () => {
      it('should track VIP badge view', () => {
        vipTelemetry.badgeViewed('header', 'medium', false);

        expect(mockLog).toHaveBeenCalledWith('vip_badge_viewed', {
          timestamp: expect.any(Number),
          component: 'header',
          variant: 'medium',
          isVip: false,
        });
      });
    });
  });

  describe('isTelemetryEnabled', () => {
    it('should return true when analytics is enabled', () => {
      mockIsAnalyticsEnabled.mockReturnValue(true);

      expect(isTelemetryEnabled()).toBe(true);
    });

    it('should return false when analytics is disabled', () => {
      mockIsAnalyticsEnabled.mockReturnValue(false);

      expect(isTelemetryEnabled()).toBe(false);
    });
  });
});

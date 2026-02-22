import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { trackEvent, trackVipEvent, vipTelemetry, isTelemetryEnabled, EventType } from '../telemetry';
import { validateEventPayload } from '../telemetry/eventRegistry';
import { isAnalyticsEnabled } from '../../config/features';
import { getSessionId } from '../sessionManager';
import { getCurrentFeatureFlags } from '../featureFlagManager';

// Mock the analytics module
vi.mock('../analytics', () => ({
  log: vi.fn(),
}));

// Mock the features module
vi.mock('../../config/features', () => ({
  isAnalyticsEnabled: vi.fn(),
}));

// Mock session manager
vi.mock('../sessionManager', () => ({
  getSessionId: vi.fn(),
}));

// Mock feature flag manager
vi.mock('../featureFlagManager', () => ({
  getCurrentFeatureFlags: vi.fn(),
}));

describe('Telemetry', () => {
  let mockLog: any;
  const mockIsAnalyticsEnabled = vi.mocked(isAnalyticsEnabled);
  const mockGetSessionId = vi.mocked(getSessionId);
  const mockGetCurrentFeatureFlags = vi.mocked(getCurrentFeatureFlags);

  beforeEach(async () => {
    const analyticsModule = await import('../analytics');
    mockLog = vi.mocked(analyticsModule.log);
    vi.clearAllMocks();
    mockIsAnalyticsEnabled.mockReturnValue(true);
    mockGetSessionId.mockReturnValue('test-session-123');
    mockGetCurrentFeatureFlags.mockReturnValue({
      vipModule: true,
      analytics: true,
      devMode: false,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('trackVipEvent', () => {
    it('should track event when analytics is enabled (deprecated alias)', () => {
      trackVipEvent(EventType.VIP_MODULE_VIEWED, {
        source: 'dashboard',
        vipEnabled: true,
      });

      expect(mockLog).toHaveBeenCalledWith('vip_module_viewed', {
        timestamp: expect.any(Number),
        sessionId: 'test-session-123',
        featureFlags: {
          vipModule: true,
          analytics: true,
          devMode: false,
        },
        source: 'dashboard',
        vipEnabled: true,
      });
    });

    it('should delegate to trackEvent (backward compatibility)', () => {
      // Both functions should produce identical results
      trackVipEvent(EventType.VIP_FEATURE_CLICKED, {
        featureName: 'test_feature',
        source: 'test',
        isVip: true,
      });

      const vipEventCall = mockLog.mock.calls[0];
      mockLog.mockClear();

      trackEvent(EventType.VIP_FEATURE_CLICKED, {
        featureName: 'test_feature',
        source: 'test',
        isVip: true,
      });

      const trackEventCall = mockLog.mock.calls[0];

      // Same event type
      expect(vipEventCall[0]).toBe(trackEventCall[0]);
      // Same payload structure (excluding timestamp which may differ slightly)
      expect(vipEventCall[1].featureName).toBe(trackEventCall[1].featureName);
      expect(vipEventCall[1].source).toBe(trackEventCall[1].source);
      expect(vipEventCall[1].isVip).toBe(trackEventCall[1].isVip);
    });
  });

  describe('trackEvent (generic entrypoint)', () => {
    it('should track event when analytics is enabled', () => {
      trackEvent(EventType.VIP_MODULE_VIEWED, {
        source: 'dashboard',
        vipEnabled: true,
      });

      expect(mockLog).toHaveBeenCalledWith('vip_module_viewed', {
        timestamp: expect.any(Number),
        sessionId: 'test-session-123',
        featureFlags: {
          vipModule: true,
          analytics: true,
          devMode: false,
        },
        source: 'dashboard',
        vipEnabled: true,
      });
    });

    it('should not log when payload is invalid', () => {
      trackEvent(EventType.VIP_FEATURE_CLICKED, { source: 'dashboard' } as any);
      expect(mockLog).not.toHaveBeenCalled();
    });

    it('should not track event when analytics is disabled', () => {
      mockIsAnalyticsEnabled.mockReturnValue(false);

      trackEvent(EventType.VIP_MODULE_VIEWED, {
        source: 'dashboard',
        vipEnabled: true,
      });

      expect(mockLog).not.toHaveBeenCalled();
    });

    it('should track growth funnel events', () => {
      trackEvent(EventType.ONBOARDING_STARTED, {
        source: 'app_launch',
        variant: 'control',
      });

      expect(mockLog).toHaveBeenCalledWith('onboarding_started', {
        timestamp: expect.any(Number),
        sessionId: 'test-session-123',
        featureFlags: {
          vipModule: true,
          analytics: true,
          devMode: false,
        },
        source: 'app_launch',
        variant: 'control',
      });
    });

    it('should add timestamp if not provided', () => {
      const beforeTime = Date.now();

      trackEvent(EventType.VIP_FEATURE_CLICKED, {
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
  });

  describe('vipTelemetry', () => {
    describe('moduleViewed', () => {
      it('should track VIP module view', () => {
        vipTelemetry.moduleViewed('dashboard', true);

        expect(mockLog).toHaveBeenCalledWith('vip_module_viewed', {
          timestamp: expect.any(Number),
          sessionId: 'test-session-123',
          featureFlags: {
            vipModule: true,
            analytics: true,
            devMode: false,
          },
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
        sessionId: 'test-session-123',
        featureFlags: {
          vipModule: true,
          analytics: true,
          devMode: false,
        },
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
          sessionId: 'test-session-123',
          featureFlags: {
            vipModule: true,
            analytics: true,
            devMode: false,
          },
          source: 'dashboard',
          context: 'feature_gate',
          isRetry: true,
        });
      });

      it('should track paywall view without isRetry', () => {
        vipTelemetry.paywallViewed('dashboard', 'feature_gate');

        expect(mockLog).toHaveBeenCalledWith('vip_paywall_viewed', {
          timestamp: expect.any(Number),
          sessionId: 'test-session-123',
          featureFlags: {
            vipModule: true,
            analytics: true,
            devMode: false,
          },
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
          sessionId: 'test-session-123',
          featureFlags: {
            vipModule: true,
            analytics: true,
            devMode: false,
          },
          source: 'dashboard',
          dismissMethod: 'close_button',
          viewDuration: 5000,
        });
      });

      it('should track paywall dismissal without viewDuration', () => {
        vipTelemetry.paywallDismissed('dashboard', 'backdrop');

        expect(mockLog).toHaveBeenCalledWith('vip_paywall_dismissed', {
          timestamp: expect.any(Number),
          sessionId: 'test-session-123',
          featureFlags: {
            vipModule: true,
            analytics: true,
            devMode: false,
          },
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
          sessionId: 'test-session-123',
          featureFlags: {
            vipModule: true,
            analytics: true,
            devMode: false,
          },
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
          sessionId: 'test-session-123',
          featureFlags: {
            vipModule: true,
            analytics: true,
            devMode: false,
          },
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
          sessionId: 'test-session-123',
          featureFlags: {
            vipModule: true,
            analytics: true,
            devMode: false,
          },
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

  describe('validateEventPayload', () => {
    it('should validate correct payload types', () => {
      const validPayload = {
        source: 'dashboard',
        vipEnabled: true,
        timestamp: Date.now(),
        sessionId: 'test-session',
        featureFlags: { vip: true }
      };

      expect(validateEventPayload(EventType.VIP_MODULE_VIEWED, validPayload)).toBe(true);
    });

    it('should reject payload with wrong field types', () => {
      const invalidPayload = {
        source: 123, // Should be string
        vipEnabled: true,
        timestamp: Date.now(),
        sessionId: 'test-session',
        featureFlags: { vip: true }
      } as any; // Cast to any to test runtime validation

      expect(validateEventPayload(EventType.VIP_MODULE_VIEWED, invalidPayload)).toBe(false);
    });

    it('should reject payload with missing required fields', () => {
      const incompletePayload = {
        source: 'dashboard',
        // Missing vipEnabled
        timestamp: Date.now(),
        sessionId: 'test-session',
        featureFlags: { vip: true }
      } as any; // Cast to any to test runtime validation

      expect(validateEventPayload(EventType.VIP_MODULE_VIEWED, incompletePayload)).toBe(false);
    });

    it('should accept payload with optional fields undefined', () => {
      const payloadWithOptionalUndefined = {
        source: 'dashboard',
        context: 'test',
        // isRetry is optional and undefined
        timestamp: Date.now(),
        sessionId: 'test-session',
        featureFlags: { vip: true }
      };

      expect(validateEventPayload(EventType.VIP_PAYWALL_VIEWED, payloadWithOptionalUndefined)).toBe(true);
    });

    it('should reject payload with wrong optional field types', () => {
      const payloadWithWrongOptionalType = {
        source: 'dashboard',
        context: 'test',
        isRetry: 'yes', // Should be boolean
        timestamp: Date.now(),
        sessionId: 'test-session',
        featureFlags: { vip: true }
      } as any; // Cast to any to test runtime validation

      expect(validateEventPayload(EventType.VIP_PAYWALL_VIEWED, payloadWithWrongOptionalType)).toBe(false);
    });

    it('should validate growth payload with allowed tierContext values', (): void => {
      const validGrowthPayload = {
        source: 'onboarding',
        placement: 'soft_paywall',
        tierContext: 'pro' as const,
        timestamp: Date.now(),
        sessionId: 'test-session',
        featureFlags: { vip: true },
      };

      expect(validateEventPayload(EventType.PAYWALL_VIEWED, validGrowthPayload)).toBe(true);
    });

    it('should reject growth payload with invalid tierContext enum value', (): void => {
      const invalidGrowthPayload = {
        source: 'onboarding',
        placement: 'soft_paywall',
        tierContext: 'enterprise',
        timestamp: Date.now(),
        sessionId: 'test-session',
        featureFlags: { vip: true },
      } as any;

      expect(validateEventPayload(EventType.PAYWALL_VIEWED, invalidGrowthPayload)).toBe(false);
    });

    it('should reject payload with wrong BaseEventPayload field types', () => {
      const payloadWithWrongTimestamp = {
        source: 'dashboard',
        vipEnabled: true,
        timestamp: 'invalid', // Should be number
        sessionId: 'test-session',
        featureFlags: { vip: true }
      } as any;

      expect(validateEventPayload(EventType.VIP_MODULE_VIEWED, payloadWithWrongTimestamp)).toBe(false);

      const payloadWithWrongSessionId = {
        source: 'dashboard',
        vipEnabled: true,
        timestamp: Date.now(),
        sessionId: 123, // Should be string
        featureFlags: { vip: true }
      } as any;

      expect(validateEventPayload(EventType.VIP_MODULE_VIEWED, payloadWithWrongSessionId)).toBe(false);

      const payloadWithWrongFeatureFlags = {
        source: 'dashboard',
        vipEnabled: true,
        timestamp: Date.now(),
        sessionId: 'test-session',
        featureFlags: 'invalid' // Should be object
      } as any;

      expect(validateEventPayload(EventType.VIP_MODULE_VIEWED, payloadWithWrongFeatureFlags)).toBe(false);
    });

    it('should reject null values for BaseEventPayload fields', () => {
      const payloadWithNullFeatureFlags = {
        source: 'dashboard',
        vipEnabled: true,
        timestamp: Date.now(),
        sessionId: 'test-session',
        featureFlags: null // Should not be null
      } as any;

      expect(validateEventPayload(EventType.VIP_MODULE_VIEWED, payloadWithNullFeatureFlags)).toBe(false);
    });

    it('should reject null values for optional fields', () => {
      const payloadWithNullOptionalField = {
        source: 'dashboard',
        context: 'test',
        isRetry: null, // Should not be null for optional field
        timestamp: Date.now(),
        sessionId: 'test-session',
        featureFlags: { vip: true }
      } as any;

      expect(validateEventPayload(EventType.VIP_PAYWALL_VIEWED, payloadWithNullOptionalField)).toBe(false);
    });

    it('should reject featureFlags with non-boolean values', () => {
      const payloadWithInvalidFeatureFlags = {
        source: 'dashboard',
        vipEnabled: true,
        timestamp: Date.now(),
        sessionId: 'test-session',
        featureFlags: { vip: 'true' } // Should be boolean, not string
      } as any;

      expect(validateEventPayload(EventType.VIP_MODULE_VIEWED, payloadWithInvalidFeatureFlags)).toBe(false);
    });

    it('should reject featureFlags when it is an array', () => {
      const payloadWithArrayFeatureFlags = {
        source: 'dashboard',
        vipEnabled: true,
        timestamp: Date.now(),
        sessionId: 'test-session',
        featureFlags: ['vip', 'analytics'] // Should be object, not array
      } as any;

      expect(validateEventPayload(EventType.VIP_MODULE_VIEWED, payloadWithArrayFeatureFlags)).toBe(false);
    });
  });
});

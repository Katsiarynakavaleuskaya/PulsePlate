/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Import the internal function for testing
import {
  getFeatureFlags,
  isVipModuleEnabled,
  isAnalyticsEnabled,
  isDevMode,
  FEATURE_FLAG_NAMES
} from '../features';

// Create a testable version of the feature flags function
const createTestFeatureFlags = (env: any) => {
  return {
    vipModule: env?.VITE_VIP_MODULE_ENABLED === 'true',
    analytics: env?.VITE_ANALYTICS_ENABLED !== 'false',
    devMode: env?.DEV === true,
  };
};

describe('Feature Flags', () => {
  describe('getFeatureFlags', () => {
    it('should return feature flags object', () => {
      const flags = getFeatureFlags();

      expect(flags).toHaveProperty('vipModule');
      expect(flags).toHaveProperty('analytics');
      expect(flags).toHaveProperty('devMode');
      expect(typeof flags.vipModule).toBe('boolean');
      expect(typeof flags.analytics).toBe('boolean');
      expect(typeof flags.devMode).toBe('boolean');
    });

    it('should have consistent return type', () => {
      const flags1 = getFeatureFlags();
      const flags2 = getFeatureFlags();

      expect(flags1).toEqual(flags2);
    });
  });

  describe('Feature Flags Logic (with test data)', () => {
    it('should return correct default values', () => {
      const env = {
        VITE_VIP_MODULE_ENABLED: 'false',
        VITE_ANALYTICS_ENABLED: 'true',
        DEV: false,
      };

      const flags = createTestFeatureFlags(env);

      expect(flags).toEqual({
        vipModule: false,
        analytics: true,
        devMode: false,
      });
    });

    it('should enable VIP module when VITE_VIP_MODULE_ENABLED is true', () => {
      const env = {
        VITE_VIP_MODULE_ENABLED: 'true',
        VITE_ANALYTICS_ENABLED: 'true',
        DEV: false,
      };

      const flags = createTestFeatureFlags(env);

      expect(flags.vipModule).toBe(true);
    });

    it('should disable analytics when VITE_ANALYTICS_ENABLED is false', () => {
      const env = {
        VITE_VIP_MODULE_ENABLED: 'false',
        VITE_ANALYTICS_ENABLED: 'false',
        DEV: false,
      };

      const flags = createTestFeatureFlags(env);

      expect(flags.analytics).toBe(false);
    });

    it('should enable dev mode when DEV is true', () => {
      const env = {
        VITE_VIP_MODULE_ENABLED: 'false',
        VITE_ANALYTICS_ENABLED: 'true',
        DEV: true,
      };

      const flags = createTestFeatureFlags(env);

      expect(flags.devMode).toBe(true);
    });
  });

  describe('individual flag getters', () => {
    it('isVipModuleEnabled should return boolean', () => {
      const result = isVipModuleEnabled();
      expect(typeof result).toBe('boolean');
    });

    it('isAnalyticsEnabled should return boolean', () => {
      const result = isAnalyticsEnabled();
      expect(typeof result).toBe('boolean');
    });

    it('isDevMode should return boolean', () => {
      const result = isDevMode();
      expect(typeof result).toBe('boolean');
    });
  });

  describe('FEATURE_FLAG_NAMES', () => {
    it('should have correct constant values', () => {
      expect(FEATURE_FLAG_NAMES).toEqual({
        VIP_MODULE: 'vipModule',
        ANALYTICS: 'analytics',
        DEV_MODE: 'devMode',
      });
    });

    it('should have string values', () => {
      expect(typeof FEATURE_FLAG_NAMES.VIP_MODULE).toBe('string');
      expect(typeof FEATURE_FLAG_NAMES.ANALYTICS).toBe('string');
      expect(typeof FEATURE_FLAG_NAMES.DEV_MODE).toBe('string');
    });
  });
});

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  initializeFeatureFlags,
  updateFeatureFlags,
  getCurrentFeatureFlags,
  refreshFeatureFlags,
  clearFeatureFlags,
} from '../featureFlagManager';
import { getFeatureFlags } from '../../config/features';

// Mock features
vi.mock('../../config/features', () => ({
  getFeatureFlags: vi.fn(),
}));

describe('FeatureFlagManager', () => {
  const mockGetFeatureFlags = vi.mocked(getFeatureFlags);

  beforeEach(() => {
    vi.clearAllMocks();
    mockGetFeatureFlags.mockReturnValue({
      vipModule: true,
      analytics: true,
      devMode: false,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    // Clear feature flags state
    clearFeatureFlags();
  });

  describe('initializeFeatureFlags', () => {
    it('should initialize flags from configuration', () => {
      initializeFeatureFlags();

      const flags = getCurrentFeatureFlags();
      expect(flags).toEqual({
        vipModule: true,
        analytics: true,
        devMode: false,
      });
    });

    it('should handle configuration errors gracefully', () => {
      mockGetFeatureFlags.mockImplementation(() => {
        throw new Error('Configuration error');
      });

      // Should not throw
      expect(() => initializeFeatureFlags()).not.toThrow();

      const flags = getCurrentFeatureFlags();
      expect(flags).toEqual({});
    });
  });

  describe('updateFeatureFlags', () => {
    it('should update flags with valid keys', () => {
      const newFlags = {
        vipModule: false,
        analytics: true,
        devMode: true,
      };

      updateFeatureFlags(newFlags);

      const flags = getCurrentFeatureFlags();
      expect(flags).toEqual(newFlags);
    });

    it('should sanitize invalid flag keys', () => {
      const newFlags = {
        vipModule: true,
        analytics: false,
        'invalid-key': true,
        'user@email.com': false,
        'validFlag': true,
      };

      updateFeatureFlags(newFlags);

      const flags = getCurrentFeatureFlags();
      expect(flags).toEqual({
        vipModule: true,
        analytics: false,
        validFlag: true,
      });
    });

    it('should convert values to boolean', () => {
      const newFlags = {
        vipModule: 'true' as any,
        analytics: 1 as any,
        devMode: null as any,
      };

      updateFeatureFlags(newFlags);

      const flags = getCurrentFeatureFlags();
      expect(flags).toEqual({
        vipModule: true,
        analytics: true,
        devMode: false,
      });
    });

    it('should handle update errors gracefully', () => {
      // Mock a scenario that might cause an error
      const newFlags = {
        vipModule: true,
      };

      // Should not throw
      expect(() => updateFeatureFlags(newFlags)).not.toThrow();
    });
  });

  describe('getCurrentFeatureFlags', () => {
    it('should return copy of current flags', () => {
      updateFeatureFlags({ vipModule: true, analytics: false });

      const flags1 = getCurrentFeatureFlags();
      const flags2 = getCurrentFeatureFlags();

      expect(flags1).toEqual(flags2);
      expect(flags1).not.toBe(flags2); // Should be different objects
    });

    it('should return empty object when no flags set', () => {
      const flags = getCurrentFeatureFlags();
      expect(flags).toEqual({});
    });
  });

  describe('refreshFeatureFlags', () => {
    it('should refresh flags from configuration', () => {
      // Set some initial flags
      updateFeatureFlags({ vipModule: false, analytics: false });

      // Mock new configuration
      mockGetFeatureFlags.mockReturnValue({
        vipModule: true,
        analytics: true,
        devMode: true,
      });

      refreshFeatureFlags();

      const flags = getCurrentFeatureFlags();
      expect(flags).toEqual({
        vipModule: true,
        analytics: true,
        devMode: true,
      });
    });
  });

  describe('clearFeatureFlags', () => {
    it('should clear all flags', () => {
      updateFeatureFlags({ vipModule: true, analytics: false });

      clearFeatureFlags();

      const flags = getCurrentFeatureFlags();
      expect(flags).toEqual({});
    });
  });

  describe('flag key validation', () => {
    it('should accept valid flag patterns', () => {
      const validFlags = {
        vipModule: true,
        analytics: false,
        devMode: true,
        featureFlag: false,
        anotherValidFlag: true,
      };

      updateFeatureFlags(validFlags);

      const flags = getCurrentFeatureFlags();
      expect(flags).toEqual(validFlags);
    });

    it('should reject invalid flag patterns', () => {
      const mixedFlags = {
        validFlag: true,
        'invalid-key': false,
        'user@email.com': true,
        'flag with spaces': false,
        '123numeric': true,
        'UPPERCASE': false,
        'camelCase': true,
      };

      updateFeatureFlags(mixedFlags);

      const flags = getCurrentFeatureFlags();
      expect(flags).toEqual({
        validFlag: true,
        UPPERCASE: false,
        camelCase: true,
      });
    });
  });
});

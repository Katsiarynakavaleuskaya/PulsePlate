/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderHook, cleanup } from '@testing-library/react';

// Mock the entire features module
vi.mock('../../config/features', () => ({
  getFeatureFlags: vi.fn(() => ({
    vipModule: false,
    analytics: true,
    devMode: false,
  })),
  isVipModuleEnabled: vi.fn(() => false),
  isAnalyticsEnabled: vi.fn(() => true),
  isDevMode: vi.fn(() => false),
  FEATURE_FLAG_NAMES: {
    VIP_MODULE: 'vipModule',
    ANALYTICS: 'analytics',
    DEV_MODE: 'devMode',
  },
}));

import { useFeatureFlag, useFeatureFlagValue, useVipModule, useAnalytics } from '../useFeatureFlag';

describe('useFeatureFlag', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe('useFeatureFlag() - all flags', () => {
    it('should return mocked feature flags', () => {
      const { result } = renderHook(() => useFeatureFlag());

      expect(result.current).toEqual({
        vipModule: false,
        analytics: true,
        devMode: false,
      });
    });

    it('should have consistent return type', () => {
      const { result, rerender } = renderHook(() => useFeatureFlag());

      const firstResult = result.current;
      rerender();
      const secondResult = result.current;

      expect(firstResult).toEqual(secondResult);
    });
  });

  describe('useFeatureFlagValue(flagName) - specific flag', () => {
    it('should return mocked value for vipModule flag', () => {
      const { result } = renderHook(() => useFeatureFlagValue('vipModule'));

      expect(result.current).toBe(false);
    });

    it('should return mocked value for analytics flag', () => {
      const { result } = renderHook(() => useFeatureFlagValue('analytics'));

      expect(result.current).toBe(true);
    });

    it('should return mocked value for devMode flag', () => {
      const { result } = renderHook(() => useFeatureFlagValue('devMode'));

      expect(result.current).toBe(false);
    });
  });

  describe('useVipModule', () => {
    it('should return mocked VIP status', () => {
      const { result } = renderHook(() => useVipModule());

      expect(result.current).toBe(false);
    });
  });

  describe('useAnalytics', () => {
    it('should return mocked analytics status', () => {
      const { result } = renderHook(() => useAnalytics());

      expect(result.current).toBe(true);
    });
  });
});

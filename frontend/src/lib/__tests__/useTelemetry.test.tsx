import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTelemetry, useVipModuleTracking } from '../useTelemetry';
import { vipTelemetry } from '../telemetry';
import { useVipModule } from '../useFeatureFlag';

// Mock the telemetry module
vi.mock('../telemetry', () => ({
  vipTelemetry: {
    moduleViewed: vi.fn(),
    featureClicked: vi.fn(),
    paywallViewed: vi.fn(),
    paywallDismissed: vi.fn(),
    upgradeClicked: vi.fn(),
    gateInteracted: vi.fn(),
    badgeViewed: vi.fn(),
  },
  isTelemetryEnabled: vi.fn(() => true),
}));

// Mock the feature flag module
vi.mock('../useFeatureFlag', () => ({
  useVipModule: vi.fn(),
}));

describe('useTelemetry', () => {
  const mockVipTelemetry = vi.mocked(vipTelemetry);
  const mockUseVipModule = vi.mocked(useVipModule);

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseVipModule.mockReturnValue(false);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('useTelemetry hook', () => {
    it('should return telemetry functions and state', () => {
      const { result } = renderHook(() => useTelemetry());

      expect(result.current).toMatchObject({
        track: expect.objectContaining({
          moduleViewed: expect.any(Function),
          featureClicked: expect.any(Function),
          paywallViewed: expect.any(Function),
          paywallDismissed: expect.any(Function),
          upgradeClicked: expect.any(Function),
          gateInteracted: expect.any(Function),
          badgeViewed: expect.any(Function),
        }),
        isEnabled: true,
        isVip: false,
      });
    });

    it('should call telemetry functions with correct parameters', () => {
      const { result } = renderHook(() => useTelemetry());

      act(() => {
        result.current.track.moduleViewed('dashboard');
      });

      expect(mockVipTelemetry.moduleViewed).toHaveBeenCalledWith('dashboard', false);
    });

    it('should pass VIP status to telemetry functions', () => {
      mockUseVipModule.mockReturnValue(true);
      const { result } = renderHook(() => useTelemetry());

      act(() => {
        result.current.track.featureClicked('advanced_analytics', 'dashboard');
      });

      expect(mockVipTelemetry.featureClicked).toHaveBeenCalledWith('advanced_analytics', 'dashboard', true);
    });

    it('should not call telemetry when disabled', async () => {
      const { isTelemetryEnabled } = await import('../telemetry');
      vi.mocked(isTelemetryEnabled).mockReturnValue(false);

      const { result } = renderHook(() => useTelemetry());

      act(() => {
        result.current.track.moduleViewed('dashboard');
      });

      expect(mockVipTelemetry.moduleViewed).not.toHaveBeenCalled();
    });

    it('should handle all telemetry functions', () => {
      const { result } = renderHook(() => useTelemetry());

      act(() => {
        result.current.track.paywallViewed('dashboard', 'feature_gate', true);
        result.current.track.paywallDismissed('dashboard', 'close_button', 5000);
        result.current.track.upgradeClicked('dashboard', 'paywall', false);
        result.current.track.gateInteracted('advanced_analytics', 'click');
        result.current.track.badgeViewed('header', 'medium');
      });

      expect(mockVipTelemetry.paywallViewed).toHaveBeenCalledWith('dashboard', 'feature_gate', true);
      expect(mockVipTelemetry.paywallDismissed).toHaveBeenCalledWith('dashboard', 'close_button', 5000);
      expect(mockVipTelemetry.upgradeClicked).toHaveBeenCalledWith('dashboard', 'paywall', false);
      expect(mockVipTelemetry.gateInteracted).toHaveBeenCalledWith('advanced_analytics', 'click', false);
      expect(mockVipTelemetry.badgeViewed).toHaveBeenCalledWith('header', 'medium', false);
    });
  });

  describe('useVipModuleTracking hook', () => {
    it('should return tracking functions and state', () => {
      const { result } = renderHook(() => useVipModuleTracking('dashboard'));

      expect(result.current).toMatchObject({
        trackView: expect.any(Function),
        isEnabled: true,
        isVip: false,
      });
    });

    it('should auto-track on mount when VIP is enabled', () => {
      mockUseVipModule.mockReturnValue(true);

      const { rerender } = renderHook(() => useVipModuleTracking('dashboard'));

      expect(mockVipTelemetry.moduleViewed).toHaveBeenCalledWith('dashboard', true);

      // Clear the mock and rerender to ensure it doesn't track again
      mockVipTelemetry.moduleViewed.mockClear();
      rerender();

      // Should not track again on re-render
      expect(mockVipTelemetry.moduleViewed).not.toHaveBeenCalled();
    });

    it('should not auto-track when VIP is disabled', () => {
      mockUseVipModule.mockReturnValue(false);

      renderHook(() => useVipModuleTracking('dashboard'));

      expect(mockVipTelemetry.moduleViewed).not.toHaveBeenCalled();
    });

    it('should not auto-track when telemetry is disabled', async () => {
      const { isTelemetryEnabled } = await import('../telemetry');
      vi.mocked(isTelemetryEnabled).mockReturnValue(false);
      mockUseVipModule.mockReturnValue(true);

      renderHook(() => useVipModuleTracking('dashboard'));

      expect(mockVipTelemetry.moduleViewed).not.toHaveBeenCalled();
    });

    it('should allow manual tracking', async () => {
      const { isTelemetryEnabled } = await import('../telemetry');
      vi.mocked(isTelemetryEnabled).mockReturnValue(true);
      mockUseVipModule.mockReturnValue(true);

      const { result } = renderHook(() => useVipModuleTracking('dashboard', false));

      act(() => {
        result.current.trackView();
      });

      expect(mockVipTelemetry.moduleViewed).toHaveBeenCalledWith('dashboard', true);
    });

    it('should not track when telemetry is disabled', async () => {
      const { isTelemetryEnabled } = await import('../telemetry');
      vi.mocked(isTelemetryEnabled).mockReturnValue(false);

      const { result } = renderHook(() => useVipModuleTracking('dashboard', false));

      act(() => {
        result.current.trackView();
      });

      expect(mockVipTelemetry.moduleViewed).not.toHaveBeenCalled();
    });
  });
});

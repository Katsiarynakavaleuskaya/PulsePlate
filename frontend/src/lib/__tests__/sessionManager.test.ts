import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getSessionId, refreshSession, clearSession, getSessionInfo } from '../sessionManager';
import { isAnalyticsEnabled } from '../../config/features';

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock crypto.getRandomValues
const mockCrypto = {
  getRandomValues: vi.fn(),
};

Object.defineProperty(window, 'crypto', {
  value: mockCrypto,
});

// Mock features
vi.mock('../../config/features', () => ({
  isAnalyticsEnabled: vi.fn(),
}));

describe('SessionManager', () => {
  const mockIsAnalyticsEnabled = vi.mocked(isAnalyticsEnabled);

  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAnalyticsEnabled.mockReturnValue(true);
    localStorageMock.getItem.mockReturnValue(null);
    mockCrypto.getRandomValues.mockImplementation((array) => {
      // Fill with predictable values for testing
      for (let i = 0; i < array.length; i++) {
        array[i] = i % 256;
      }
      return array;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('getSessionId', () => {
    it('should return "disabled" when analytics is disabled', () => {
      mockIsAnalyticsEnabled.mockReturnValue(false);

      const sessionId = getSessionId();

      expect(sessionId).toBe('disabled');
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });

    it('should create new session when none exists', () => {
      localStorageMock.getItem.mockReturnValue(null);

      const sessionId = getSessionId();

      expect(sessionId).toMatch(/^[A-Za-z0-9]{16}$/);
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'pp_telemetry_session',
        expect.stringContaining(sessionId)
      );
    });

    it('should return existing valid session', () => {
      const existingSession = {
        sessionId: 'existing123456',
        createdAt: Date.now() - 1000,
        expiresAt: Date.now() + 3600000, // 1 hour from now
      };
      localStorageMock.getItem.mockReturnValue(JSON.stringify(existingSession));

      const sessionId = getSessionId();

      expect(sessionId).toBe('existing123456');
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });

    it('should create new session when existing one is expired', () => {
      const expiredSession = {
        sessionId: 'expired123456',
        createdAt: Date.now() - 3600000,
        expiresAt: Date.now() - 1000, // Expired
      };
      localStorageMock.getItem.mockReturnValue(JSON.stringify(expiredSession));

      const sessionId = getSessionId();

      expect(sessionId).not.toBe('expired123456');
      expect(sessionId).toMatch(/^[A-Za-z0-9]{16}$/);
      expect(localStorageMock.setItem).toHaveBeenCalled();
    });

    it('should handle localStorage errors gracefully', () => {
      localStorageMock.getItem.mockImplementation(() => {
        throw new Error('localStorage error');
      });

      const sessionId = getSessionId();

      expect(sessionId).toMatch(/^[A-Za-z0-9]{16}$/);
      expect(localStorageMock.setItem).toHaveBeenCalled();
    });

    it('should handle invalid JSON gracefully', () => {
      localStorageMock.getItem.mockReturnValue('invalid json');

      const sessionId = getSessionId();

      expect(sessionId).toMatch(/^[A-Za-z0-9]{16}$/);
      expect(localStorageMock.setItem).toHaveBeenCalled();
    });
  });

  describe('refreshSession', () => {
    it('should return "disabled" when analytics is disabled', () => {
      mockIsAnalyticsEnabled.mockReturnValue(false);

      const sessionId = refreshSession();

      expect(sessionId).toBe('disabled');
    });

    it('should refresh valid session', () => {
      const validSession = {
        sessionId: 'valid123456',
        createdAt: Date.now() - 1000,
        expiresAt: Date.now() + 3600000,
      };
      localStorageMock.getItem.mockReturnValue(JSON.stringify(validSession));

      const sessionId = refreshSession();

      expect(sessionId).toBe('valid123456');
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'pp_telemetry_session',
        expect.stringContaining('valid123456')
      );
    });

    it('should create new session when refreshing expired one', () => {
      const expiredSession = {
        sessionId: 'expired123456',
        createdAt: Date.now() - 3600000,
        expiresAt: Date.now() - 1000,
      };
      localStorageMock.getItem.mockReturnValue(JSON.stringify(expiredSession));

      const sessionId = refreshSession();

      expect(sessionId).not.toBe('expired123456');
      expect(sessionId).toMatch(/^[A-Za-z0-9]{16}$/);
    });

    it('should create new session when no session exists', () => {
      localStorageMock.getItem.mockReturnValue(null);

      const sessionId = refreshSession();

      expect(sessionId).toMatch(/^[A-Za-z0-9]{16}$/);
      expect(localStorageMock.setItem).toHaveBeenCalled();
    });
  });

  describe('clearSession', () => {
    it('should remove session from localStorage', () => {
      clearSession();

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('pp_telemetry_session');
    });

    it('should handle localStorage errors gracefully', () => {
      localStorageMock.removeItem.mockImplementation(() => {
        throw new Error('localStorage error');
      });

      // Should not throw
      expect(() => clearSession()).not.toThrow();
    });
  });

  describe('getSessionInfo', () => {
    it('should return disabled info when analytics is disabled', () => {
      mockIsAnalyticsEnabled.mockReturnValue(false);

      const info = getSessionInfo();

      expect(info).toEqual({
        sessionId: 'disabled',
        isExpired: false,
        timeRemaining: 0,
      });
    });

    it('should return session info for valid session', () => {
      const validSession = {
        sessionId: 'valid123456',
        createdAt: Date.now() - 1000,
        expiresAt: Date.now() + 3600000,
      };
      localStorageMock.getItem.mockReturnValue(JSON.stringify(validSession));

      const info = getSessionInfo();

      expect(info.sessionId).toBe('valid123456');
      expect(info.isExpired).toBe(false);
      expect(info.timeRemaining).toBeGreaterThan(0);
    });

    it('should return expired info for expired session', () => {
      const expiredSession = {
        sessionId: 'expired123456',
        createdAt: Date.now() - 3600000,
        expiresAt: Date.now() - 1000,
      };
      localStorageMock.getItem.mockReturnValue(JSON.stringify(expiredSession));

      const info = getSessionInfo();

      expect(info.sessionId).toBe('expired123456');
      expect(info.isExpired).toBe(true);
      expect(info.timeRemaining).toBe(0);
    });

    it('should return none info when no session exists', () => {
      localStorageMock.getItem.mockReturnValue(null);

      const info = getSessionInfo();

      expect(info).toEqual({
        sessionId: 'none',
        isExpired: true,
        timeRemaining: 0,
      });
    });

    it('should handle errors gracefully', () => {
      localStorageMock.getItem.mockImplementation(() => {
        throw new Error('localStorage error');
      });

      const info = getSessionInfo();

      expect(info).toEqual({
        sessionId: 'error',
        isExpired: true,
        timeRemaining: 0,
      });
    });
  });
});

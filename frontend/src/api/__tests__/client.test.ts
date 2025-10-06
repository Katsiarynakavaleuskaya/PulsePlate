// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fetchJson, validateApiKey } from '../client';

// Mock fetch globally
const fetchMock = vi.fn();
global.fetch = fetchMock;

describe('API Client Auth', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock localStorage/sessionStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: vi.fn(),
        setItem: vi.fn(),
        removeItem: vi.fn(),
      },
      writable: true,
    });
    Object.defineProperty(window, 'sessionStorage', {
      value: {
        getItem: vi.fn(),
        setItem: vi.fn(),
        removeItem: vi.fn(),
      },
      writable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('401 Error Handling', () => {
    it('should clear API key and redirect on 401 response', async () => {
      // Mock 401 response
      fetchMock.mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: () => Promise.resolve('Unauthorized'),
      });

      // Mock window.location
      const locationMock = { href: '' };
      Object.defineProperty(window, 'location', {
        value: locationMock,
        writable: true,
      });

      // Attempt API call
      await expect(fetchJson('/test')).rejects.toThrow('API key invalid or expired');

      // Verify localStorage/sessionStorage cleanup
      expect(window.localStorage.removeItem).toHaveBeenCalledWith('pulseplate_api_key');
      expect(window.sessionStorage.removeItem).toHaveBeenCalledWith('pulseplate_api_key');

      // Verify redirect
      expect(window.location.href).toBe('/enter-key');
    });
  });

  describe('validateApiKey', () => {
    it('should return true for successful validation', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'ok' }),
      });

      const result = await validateApiKey();
      expect(result).toBe(true);
    });

    it('should return false for 401 Unauthorized response', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ error: 'Unauthorized' }),
      });

      const result = await validateApiKey();
      expect(result).toBe(false);
    });

    it('should return false for failed validation', async () => {
      fetchMock.mockRejectedValueOnce(new Error('Network error'));

      const result = await validateApiKey();
      expect(result).toBe(false);
    });
  });
});

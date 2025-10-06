// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock the entire client module
vi.mock('../client', () => ({
  validateApiKey: vi.fn(),
  fetchJson: vi.fn(),
}));

import { validateApiKey, fetchJson } from '../client';

// Mock fetch globally
const fetchMock = vi.fn();
global.fetch = fetchMock;

describe('API Client Auth', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('401 Error Handling', () => {
    it('should clear API key and redirect on 401 response', async () => {
      // Mock timers
      vi.useFakeTimers();

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

      // Fast-forward timers to trigger redirect
      vi.advanceTimersByTime(100);

      // Verify redirect
      expect(window.location.href).toBe('/enter-key');

      vi.useRealTimers();
    });
  });

  describe('validateApiKey', () => {
    it('should return true for successful validation', async () => {
      (validateApiKey as any).mockResolvedValue(true);

      const result = await validateApiKey();
      expect(result).toBe(true);
    });

    it('should return false for failed validation', async () => {
      (validateApiKey as any).mockResolvedValue(false);

      const result = await validateApiKey();
      expect(result).toBe(false);
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
  });
});

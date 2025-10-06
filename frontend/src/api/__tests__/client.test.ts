// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock auth storage functions
const mockStorage = {
  getStoredApiKey: vi.fn(() => 'test-api-key'),
  setStoredApiKey: vi.fn(),
  clearStoredApiKey: vi.fn(),
};
vi.mock('../auth/storage', () => mockStorage);

// Глобальный мок fetch для Vitest (jsdom окружение)
// Global fetch mock for Vitest (jsdom environment)
const fetchMock = vi.fn();
(globalThis as any).fetch = fetchMock;

describe('API Client Auth', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('validateApiKey', () => {
    it('returns false on network error', async () => {
      const originalImport = (globalThis as any).import;
      (globalThis as any).import = {
        meta: {
          env: {
            VITE_API_BASE: 'http://test-api.com',
          },
        },
      };

      const { validateApiKey } = await import('../client');
      fetchMock.mockRejectedValueOnce(new Error('Network error'));

      const result = await validateApiKey();
      expect(result).toBe(false);

      (globalThis as any).import = originalImport;
    });

    it('should return false for 401 on health check (mockResolvedValueOnce)', async () => {
      const originalImport = (globalThis as any).import;
      (globalThis as any).import = {
        meta: {
          env: {
            VITE_API_BASE: 'http://test-api.com',
          },
        },
      };

      const { validateApiKey } = await import('../client');
      fetchMock.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ error: 'Unauthorized' }),
      });

      const result = await validateApiKey();
      expect(result).toBe(false);

      (globalThis as any).import = originalImport;
    });
  });
});

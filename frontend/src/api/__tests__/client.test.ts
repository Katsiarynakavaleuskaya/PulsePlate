// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock auth storage functions
const mockStorage = {
  getStoredApiKey: vi.fn(() => 'test-api-key'),
  setStoredApiKey: vi.fn(),
  clearStoredApiKey: vi.fn(),
};
vi.mock('../../auth/storage', () => mockStorage);

// Set test API base globally for all tests
(globalThis as any).__TEST_API_BASE__ = 'http://test-api.com';

// Set test storage functions globally for all tests
const testStorage = {
  getStoredApiKey: vi.fn(() => null as string | null),
  setStoredApiKey: vi.fn(),
  clearStoredApiKey: vi.fn(),
};
(globalThis as any).__TEST_getStoredApiKey__ = testStorage.getStoredApiKey;
(globalThis as any).__TEST_clearStoredApiKey__ = testStorage.clearStoredApiKey;

// Mock window.location.replace to prevent jsdom errors
const originalLocation = window.location;
Object.defineProperty(window, 'location', {
  value: { ...originalLocation, replace: vi.fn() },
  writable: true,
});

// Глобальный мок fetch для Vitest (jsdom окружение)
// Global fetch mock for Vitest (jsdom environment)
const fetchMock = vi.fn(() => Promise.resolve(new Response('{}', { status: 200 })));
(globalThis as any).fetch = fetchMock;

// Helper to create a proper Response mock
const createMockResponse = (options: { ok: boolean; status: number; json?: () => Promise<any> }) => {
  const response = new Response(JSON.stringify(options.json ? options.json() : {}), {
    status: options.status,
    statusText: options.ok ? 'OK' : 'Error',
  });
  // Override the json method to return the expected data
  response.json = options.json || (() => Promise.resolve({}));
  return response;
};

describe('API Client Auth', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  describe('validateApiKey', () => {
    it('returns false on network error', async () => {
      vi.stubEnv('VITE_API_BASE', 'http://test-api.com');

      const { validateApiKey } = await import('../client');
      fetchMock.mockRejectedValueOnce(new Error('Network error'));

      const result = await validateApiKey();
      expect(result).toBe(false);
    });

    it('should return false for 401 on health check (mockResolvedValueOnce)', async () => {
      vi.stubEnv('VITE_API_BASE', 'http://test-api.com');

      const { validateApiKey } = await import('../client');
      fetchMock.mockResolvedValueOnce(new Response('{"error": "Unauthorized"}', { status: 401 }));

      const result = await validateApiKey();
      expect(result).toBe(false);
    });
  });

  describe('api() function', () => {
    it('includes X-API-Key header when API key is set in storage', async () => {
      vi.stubEnv('VITE_API_BASE', 'http://test-api.com');
      testStorage.getStoredApiKey.mockReturnValue('test-api-key');

      const { api } = await import('../client');

      (fetchMock as any).mockImplementationOnce((input: any, options?: any) => {
        const url = typeof input === 'string' ? input : input.url;
        expect(url).toBe('http://test-api.com/test-endpoint');
        const requestOptions = typeof input === 'string' ? options : input;
        expect(requestOptions.headers.get('X-API-Key')).toBe('test-api-key');
        return Promise.resolve(createMockResponse({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ data: 'test' }),
        }));
      });

      await api('/test-endpoint');

      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    it('clears storage and calls navigate callback on 401 response', async () => {
      vi.stubEnv('VITE_API_BASE', 'http://test-api.com');
      const mockNavigate = vi.fn();

      const { api } = await import('../client');
      fetchMock.mockImplementationOnce(() => Promise.resolve(createMockResponse({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ error: 'Unauthorized' }),
      })));

      await expect(api('/test-endpoint', {}, mockNavigate)).rejects.toThrow('API key invalid or expired.');

      expect(testStorage.clearStoredApiKey).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith('/enter-key');
    });

    it('clears storage and uses window.location.replace when no navigate callback on 401', async () => {
      vi.stubEnv('VITE_API_BASE', 'http://test-api.com');
      const { api } = await import('../client');
      fetchMock.mockImplementationOnce(() => Promise.resolve(createMockResponse({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ error: 'Unauthorized' }),
      })));

      await expect(api('/test-endpoint')).rejects.toThrow('API key invalid or expired.');

      expect(testStorage.clearStoredApiKey).toHaveBeenCalled();
      expect(window.location.replace).toHaveBeenCalledWith('/enter-key');
    });

    it('throws UnauthorizedError on 401 response', async () => {
      vi.stubEnv('VITE_API_BASE', 'http://test-api.com');
      const { api, UnauthorizedError } = await import('../client');
      fetchMock.mockImplementationOnce(() => Promise.resolve(new Response('{"error": "Unauthorized"}', { status: 401 } as any)));

      await expect(api('/test-endpoint')).rejects.toThrow(UnauthorizedError);
    });

    it('uses mock fallback on network failure', async () => {
      vi.stubEnv('VITE_API_BASE', 'http://test-api.com');
      const { api } = await import('../client');

      // Mock fetch to behave differently based on URL
      let callCount = 0;
      (fetchMock as any).mockImplementation((input: any) => {
        const url = typeof input === 'string' ? input : (input instanceof Request ? input.url : 'unknown');
        callCount++;
        if (url === 'http://test-api.com/premium/bmr') {
          // Network call fails
          return Promise.reject(new Error('Network error'));
        } else if (url === 'http://localhost:3000/mock/bmr.json') {
          // Mock call succeeds
          return Promise.resolve(new Response('{"mock": true}', { status: 200 }));
        }
        return Promise.reject(new Error(`Unexpected URL: ${url}`));
      });

      const result = await api('/premium/bmr');

      expect(result).toEqual({ mock: true });
      expect(callCount).toBe(2);
    });

    it('resolves successfully on authenticated request', async () => {
      vi.stubEnv('VITE_API_BASE', 'http://test-api.com');
      testStorage.getStoredApiKey.mockReturnValue('valid-api-key');

      const { api } = await import('../client');
      const mockResponse = { success: true, data: 'authenticated' };
      fetchMock.mockImplementationOnce(() => Promise.resolve(createMockResponse({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
      })));

      const result = await api('/test-endpoint');

      expect(result).toEqual(mockResponse);
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });
  });

});

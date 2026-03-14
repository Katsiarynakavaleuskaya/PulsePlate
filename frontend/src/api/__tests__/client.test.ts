// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock auth storage functions
const testStorage = {
  getStoredApiKey: vi.fn(() => null as string | null),
  setStoredApiKey: vi.fn(),
  clearStoredApiKey: vi.fn(),
};
vi.mock('../../auth/storage', () => testStorage);

// Mock window.location.replace to prevent jsdom errors
const originalLocation = window.location;
Object.defineProperty(window, 'location', {
  value: { ...originalLocation, replace: vi.fn() },
  writable: true,
});

// Глобальный мок fetch для Vitest (jsdom окружение)
// Global fetch mock for Vitest (jsdom environment)
const fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>(
  () => Promise.resolve(new Response('{}', { status: 200 }))
);
(globalThis as any).fetch = fetchMock;

// Helper to create a proper Response mock
const createMockResponse = (data: any, options: { ok: boolean; status: number }) => {
  return new Response(JSON.stringify(data), {
    status: options.status,
    statusText: options.ok ? 'OK' : 'Error',
  });
};

describe('API Client Auth', () => {
  beforeEach(async () => {
    vi.resetAllMocks();
    // Reset mock implementations/state
    fetchMock.mockReset();
    testStorage.getStoredApiKey.mockReset();
    testStorage.setStoredApiKey.mockReset();
    testStorage.clearStoredApiKey.mockReset();
    // Default behaviors for each test
    testStorage.getStoredApiKey.mockReturnValue(null);
    fetchMock.mockImplementation(() => Promise.resolve(new Response('{}', { status: 200 })));
    vi.stubEnv('VITE_API_BASE', 'http://test-api.com');

    // Set up test dependencies using dependency injection
    const { setApiClientDependencies } = await import('../client');
    setApiClientDependencies({
      getStoredApiKey: testStorage.getStoredApiKey,
      clearStoredApiKey: testStorage.clearStoredApiKey,
      apiBase: 'http://test-api.com',
    });
  });

  afterEach(async () => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    // Restore original window.location to prevent state leaks between tests
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      writable: true,
    });
    // Reset dependencies to prevent state leaks between tests
    const { setApiClientDependencies } = await import('../client');
    setApiClientDependencies(null);
  });

  describe('validateApiKey', () => {
    it('returns false on network error', async () => {
      const { validateApiKey } = await import('../client');
      fetchMock.mockRejectedValueOnce(new Error('Network error'));

      const result = await validateApiKey();
      expect(result).toBe(false);
    });

    it('should return false for 401 on health check (mockResolvedValueOnce)', async () => {
      const { validateApiKey } = await import('../client');
      fetchMock.mockResolvedValueOnce(new Response('{"error": "Unauthorized"}', { status: 401 }));

      const result = await validateApiKey();
      expect(result).toBe(false);
    });

    it('throws error when API base is not set', async () => {
      const { validateApiKey, setApiClientDependencies } = await import('../client');

      // Temporarily set API base to empty string
      setApiClientDependencies({
        getStoredApiKey: testStorage.getStoredApiKey,
        clearStoredApiKey: testStorage.clearStoredApiKey,
        apiBase: '',
      });

      await expect(validateApiKey()).rejects.toThrow('VITE_API_BASE is not set');
    });
  });

  describe('api() function', () => {
    it('throws error when API base is not set', async () => {
      const { api, setApiClientDependencies } = await import('../client');

      // Temporarily set API base to empty string
      setApiClientDependencies({
        getStoredApiKey: testStorage.getStoredApiKey,
        clearStoredApiKey: testStorage.clearStoredApiKey,
        apiBase: '',
      });

      await expect(api('/test-endpoint')).rejects.toThrow('VITE_API_BASE is not set');
    });

    it('does not attach X-API-Key header for regular API calls', async () => {
      const { api } = await import('../client');

      fetchMock.mockImplementationOnce((input: any, options?: any) => {
        const url = typeof input === 'string' ? input : input.url;
        expect(url).toBe('http://test-api.com/test-endpoint');
        const requestOptions = typeof input === 'string' ? options : input;
        expect(requestOptions.credentials).toBe('include');
        expect(requestOptions.headers.get('X-API-Key')).toBeNull();
        return Promise.resolve(createMockResponse({ data: 'test' }, {
          ok: true,
          status: 200,
        }));
      });

      await api('/test-endpoint');

      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    it('clears storage and uses window.location.replace when no onAuthError callback on 401', async () => {
      const { api } = await import('../client');
      fetchMock.mockImplementationOnce(() => Promise.resolve(createMockResponse({ error: 'Unauthorized' }, {
        ok: false,
        status: 401,
      })));

      await expect(api('/test-endpoint')).rejects.toThrow('Session invalid or expired (401).');

      expect(testStorage.clearStoredApiKey).toHaveBeenCalled();
      expect(window.location.replace).toHaveBeenCalledWith('/enter-key');
    });

    it('throws UnauthorizedError on 401 response', async () => {
      const { api, UnauthorizedError } = await import('../client');
      fetchMock.mockImplementationOnce(() =>
        Promise.resolve(createMockResponse({ error: 'Unauthorized' }, { ok: false, status: 401 }))
      );

      await expect(api('/test-endpoint')).rejects.toThrow(UnauthorizedError);
    });

    it('uses mock fallback on network failure', async () => {
      const { api } = await import('../client');

      // Mock fetch to behave differently based on URL pattern
      fetchMock.mockImplementation((input: any) => {
        const url = typeof input === 'string' ? input : (input instanceof Request ? input.url : 'unknown');
        if (url.includes('/premium/bmr') && !url.includes('mock')) {
          // Primary API call fails
          return Promise.reject(new Error('Network error'));
        } else if (url.includes('mock') && url.includes('bmr')) {
          // Mock fallback succeeds
          return Promise.resolve(createMockResponse({ mock: true }, { ok: true, status: 200 }));
        }
        return Promise.reject(new Error('Network error'));
      });

      const result = await api('/premium/bmr');

      expect(result).toEqual({ mock: true });
      expect(fetchMock).toHaveBeenCalled();
    });

    it('resolves successfully on authenticated request', async () => {
      const { api } = await import('../client');
      const mockResponse = { success: true, data: 'authenticated' };
      fetchMock.mockImplementationOnce(() => Promise.resolve(createMockResponse(mockResponse, {
        ok: true,
        status: 200,
      })));

      const result = await api('/test-endpoint');

      expect(result).toEqual(mockResponse);
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });
  });

  describe('server-session helpers', () => {
    it('getProSessionStatus returns canonical session payload', async () => {
      const { getProSessionStatus } = await import('../client');
      fetchMock.mockImplementationOnce(async (input: RequestInfo | URL, init?: RequestInit) => {
        const request = input instanceof Request ? input : new Request(input, init);
        expect(request.url).toBe('http://test-api.com/api/v1/pro/session');
        return createMockResponse(
          { status: 'ok', authenticated: true, auth_source: 'cookie', tier: 'PRO' },
          { ok: true, status: 200 }
        );
      });

      await expect(getProSessionStatus()).resolves.toEqual({
        status: 'ok',
        authenticated: true,
        auth_source: 'cookie',
        tier: 'PRO',
      });
    });

    it('checkProSession returns true for authenticated response', async () => {
      const { checkProSession } = await import('../client');
      fetchMock.mockImplementationOnce(async (input: RequestInfo | URL, init?: RequestInit) => {
        const request = input instanceof Request ? input : new Request(input, init);
        expect(request.url).toBe('http://test-api.com/api/v1/pro/session');
        expect(request.method).toBe('GET');
        expect(request.credentials).toBe('include');
        return createMockResponse(
          { status: 'ok', authenticated: true, auth_source: 'cookie', tier: 'PRO' },
          { ok: true, status: 200 }
        );
      });

      await expect(checkProSession()).resolves.toBe(true);
    });

    it('checkProSession returns false for unauthorized response', async () => {
      const { checkProSession } = await import('../client');
      fetchMock.mockResolvedValueOnce(createMockResponse({}, { ok: false, status: 401 }));

      await expect(checkProSession()).resolves.toBe(false);
    });

    it('checkProSession fails closed for unknown payload shape', async () => {
      const { checkProSession } = await import('../client');
      fetchMock.mockResolvedValueOnce(createMockResponse({ status: 'ok' }, { ok: true, status: 200 }));

      await expect(checkProSession()).resolves.toBe(false);
    });

    it('getProSessionStatus fails closed for malformed session payload', async () => {
      const { getProSessionStatus } = await import('../client');
      fetchMock.mockResolvedValueOnce(createMockResponse({ status: 'ok' }, { ok: true, status: 200 }));

      await expect(getProSessionStatus()).resolves.toBeNull();
    });

    it('exchangeApiKeyForSession posts exchange payload and returns true', async () => {
      const { exchangeApiKeyForSession } = await import('../client');

      fetchMock.mockImplementationOnce(async (input: RequestInfo | URL, init?: RequestInit) => {
        const request = input instanceof Request ? input : new Request(input, init);
        expect(request.url).toBe('http://test-api.com/api/v1/pro/session/exchange');
        expect(request.method).toBe('POST');
        expect(request.credentials).toBe('include');
        expect(request.headers.get('X-API-Key')).toBe('test-session-key');
        return createMockResponse({ authenticated: true }, { ok: true, status: 200 });
      });

      await expect(exchangeApiKeyForSession('test-session-key')).resolves.toBe(true);
    });

    it('clearProSession calls logout endpoint with POST', async () => {
      const { clearProSession } = await import('../client');

      fetchMock.mockImplementationOnce(async (input: RequestInfo | URL, init?: RequestInit) => {
        const request = input instanceof Request ? input : new Request(input, init);
        expect(request.url).toBe('http://test-api.com/api/v1/pro/session/logout');
        expect(request.method).toBe('POST');
        expect(request.credentials).toBe('include');
        return createMockResponse({ status: 'ok' }, { ok: true, status: 200 });
      });

      await expect(clearProSession()).resolves.toBeUndefined();
    });
  });

});

/**
 * Unit tests for fetchBlob() security contract
 *
 * RU: Тесты безопасности для fetchBlob() — credentials и auth headers.
 * EN: Security contract tests for fetchBlob() — credentials and auth headers.
 *
 * These tests verify the critical security invariant:
 * - External URLs MUST NOT receive API credentials (headers or cookies)
 * - API paths MUST include credentials
 * - Auth errors (401/403) on API paths trigger key clearing and redirect
 *
 * Implementation: Uses vi.stubGlobal + setApiClientDependencies (no MSW).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fetchBlob, setApiClientDependencies } from '../client';

describe('fetchBlob security contract', () => {
  // Store original fetch and window.location
  const originalFetch = globalThis.fetch;
  const originalLocation = window.location;

  // Test dependencies
  const mockClearStoredApiKey = vi.fn();
  const mockGetStoredApiKey = vi.fn(() => 'test-api-key');

  // Captured fetch calls for assertions
  let capturedUrl: string | undefined;
  let capturedInit: RequestInit | undefined;

  beforeEach(() => {
    // Reset mocks
    mockClearStoredApiKey.mockClear();
    mockGetStoredApiKey.mockClear();
    capturedUrl = undefined;
    capturedInit = undefined;

    // Inject test dependencies
    setApiClientDependencies({
      getStoredApiKey: mockGetStoredApiKey,
      clearStoredApiKey: mockClearStoredApiKey,
      apiBase: 'https://api.test.com',
    });

    // Mock window.location.replace
    Object.defineProperty(window, 'location', {
      value: { replace: vi.fn() },
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    // Restore original fetch
    globalThis.fetch = originalFetch;

    // Restore window.location
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      writable: true,
      configurable: true,
    });

    // Reset dependencies
    setApiClientDependencies(null);
  });

  describe('Test 1: Absolute URL — credentials omit + headers stripped', () => {
    it('should strip auth headers and force credentials:omit for external URLs', async () => {
      // Stub fetch to capture the call and return success
      const mockBlob = new Blob(['test-data']);
      vi.stubGlobal('fetch', vi.fn((url: string, init?: RequestInit) => {
        capturedUrl = url;
        capturedInit = init;
        return Promise.resolve({
          ok: true,
          status: 200,
          blob: () => Promise.resolve(mockBlob),
        } as Response);
      }));

      // Call fetchBlob with external URL + dangerous headers
      await fetchBlob('https://external.storage.com/signed-file?token=abc', {
        headers: {
          'Authorization': 'Bearer secret-token',
          'X-API-Key': 'secret-key',
          'Content-Type': 'application/octet-stream',
        },
        credentials: 'include', // Caller tries to include credentials
      });

      // Verify URL was NOT prepended with API base
      expect(capturedUrl).toBe('https://external.storage.com/signed-file?token=abc');

      // Verify credentials forced to 'omit' (security: no cookies to external)
      expect(capturedInit?.credentials).toBe('omit');

      // Verify auth headers were stripped (security: no API key leak)
      const headers = capturedInit?.headers as Headers;
      expect(headers.get('Authorization')).toBeNull();
      expect(headers.get('authorization')).toBeNull();
      expect(headers.get('X-API-Key')).toBeNull();
      expect(headers.get('x-api-key')).toBeNull();

      // Verify non-auth headers preserved
      expect(headers.get('Content-Type')).toBe('application/octet-stream');
    });
  });

  describe('Test 2: API path — credentials include by default', () => {
    it('should include credentials and prepend API base for API paths', async () => {
      // Stub fetch to capture the call and return success
      const mockBlob = new Blob(['api-data']);
      vi.stubGlobal('fetch', vi.fn((url: string, init?: RequestInit) => {
        capturedUrl = url;
        capturedInit = init;
        return Promise.resolve({
          ok: true,
          status: 200,
          blob: () => Promise.resolve(mockBlob),
        } as Response);
      }));

      // Call fetchBlob with API path (no explicit credentials)
      await fetchBlob('/api/v1/export.pdf');

      // Verify URL was prepended with API base
      expect(capturedUrl).toBe('https://api.test.com/api/v1/export.pdf');

      // Verify credentials default to 'include'
      expect(capturedInit?.credentials).toBe('include');
    });
  });

  describe('Test 3: 401/403 on API path — clear key + redirect', () => {
    it('should clear API key and redirect on 401 for API paths', async () => {
      // Stub fetch to return 401
      vi.stubGlobal('fetch', vi.fn(() => {
        return Promise.resolve({
          ok: false,
          status: 401,
        } as Response);
      }));

      // Call fetchBlob with API path, expect it to throw
      await expect(fetchBlob('/api/v1/protected')).rejects.toThrow(/401/);

      // Verify key was cleared
      expect(mockClearStoredApiKey).toHaveBeenCalledTimes(1);

      // Verify redirect to /enter-key
      expect(window.location.replace).toHaveBeenCalledWith('/enter-key');
    });

    it('should NOT clear key or redirect on 401 for external URLs', async () => {
      // Stub fetch to return 401
      vi.stubGlobal('fetch', vi.fn(() => {
        return Promise.resolve({
          ok: false,
          status: 401,
        } as Response);
      }));

      // Call fetchBlob with external URL, expect generic error
      await expect(fetchBlob('https://external.com/file')).rejects.toThrow('HTTP 401');

      // Verify key was NOT cleared (external 401 is not our auth issue)
      expect(mockClearStoredApiKey).not.toHaveBeenCalled();

      // Verify NO redirect (external auth failure should not affect our app state)
      expect(window.location.replace).not.toHaveBeenCalled();
    });
  });
});

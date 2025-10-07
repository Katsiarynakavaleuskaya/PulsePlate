// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api, setApiClientDependencies } from '../client';

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

describe('API Auth Error Callbacks', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    fetchMock.mockReset();
    fetchMock.mockImplementation(() => Promise.resolve(new Response('{}', { status: 200 })));
    vi.stubEnv('VITE_API_BASE', 'http://test-api.com');

    // Set up test dependencies
    setApiClientDependencies({
      getStoredApiKey: () => null,
      clearStoredApiKey: () => {},
      apiBase: 'http://test-api.com',
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it('invokes onAuthError from 3rd param on 401', async () => {
    fetchMock.mockImplementationOnce(() => Promise.resolve(createMockResponse({ error: 'Unauthorized' }, {
      ok: false,
      status: 401,
    })));

    const handler = vi.fn();
    await expect(api('/probe', undefined, { onAuthError: (c, h) => handler(c, h) }))
      .rejects.toBeTruthy();

    expect(handler).toHaveBeenCalledWith(401, expect.objectContaining({ clearApiKey: expect.any(Function) }));
  });

  it('invokes onAuthError from 3rd param on 403', async () => {
    fetchMock.mockImplementationOnce(() => Promise.resolve(createMockResponse({ error: 'Forbidden' }, {
      ok: false,
      status: 403,
    })));

    const handler = vi.fn();
    await expect(api('/probe', undefined, { onAuthError: (c, h) => handler(c, h) }))
      .rejects.toBeTruthy();

    expect(handler).toHaveBeenCalledWith(403, expect.objectContaining({ clearApiKey: expect.any(Function) }));
  });

  it('falls back to clear+redirect when onAuthError is not provided (401)', async () => {
    fetchMock.mockImplementationOnce(() => Promise.resolve(createMockResponse({ error: 'Unauthorized' }, {
      ok: false,
      status: 401,
    })));

    const clearSpy = vi.fn();
    // inject dependencies to simulate stored key behavior
    setApiClientDependencies({
      apiBase: 'http://test-api.com',
      getStoredApiKey: () => 'TEST_KEY',
      clearStoredApiKey: clearSpy,
    });

    // mock location.replace
    const replaceSpy = vi.fn();
    Object.defineProperty(window, 'location', {
      value: { replace: replaceSpy },
      writable: true
    });

    await expect(api('/probe')).rejects.toBeTruthy();

    expect(clearSpy).toHaveBeenCalledTimes(1);
    expect(replaceSpy).toHaveBeenCalledWith('/enter-key');
  });
});

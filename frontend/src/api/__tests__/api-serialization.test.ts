// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api, setApiClientDependencies } from '../client';

describe('API Body Serialization', () => {
  beforeEach(async () => {
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
    // Reset dependencies
    setApiClientDependencies(null);
  });

  it('serializes body to JSON in api() and sets Content-Type only when needed', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch' as any).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
      url: 'http://test-api.com/test',
    } as Response);

    const body = { a: 1, b: 'x' };
    await api('/test', { method: 'POST', body });

    const [, init] = fetchSpy.mock.calls[0];
    // body is serialized string passed into fetch
    expect(typeof init.body).toBe('string');
    expect(init.body).toBe(JSON.stringify(body));
    // header check via Headers API to handle both object and Headers cases
    const headers =
      init.headers instanceof Headers ? init.headers : new Headers(init.headers);
    expect(headers.has('Content-Type')).toBe(true);
    expect(headers.get('Content-Type')).toBe('application/json');

    fetchSpy.mockRestore();
  });

  it('does not set Content-Type for GET without body', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch' as any).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
      url: 'http://test-api.com/ping',
    } as Response);

    await api('/ping', { method: 'GET' });

    const [, init] = fetchSpy.mock.calls[0];
    const headers =
      init.headers instanceof Headers ? init.headers : new Headers(init.headers);
    expect(headers.has('Content-Type')).toBe(false);

    fetchSpy.mockRestore();
  });
});

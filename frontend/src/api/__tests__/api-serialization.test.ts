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

    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(typeof init.body).toBe('string');
    expect(init.headers instanceof Headers && init.headers.get('Content-Type')).toBe('application/json');

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

    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    const headers = init.headers instanceof Headers ? init.headers : new Headers(init.headers as HeadersInit);
    expect(headers.has('Content-Type')).toBe(false);

    fetchSpy.mockRestore();
  });

  it('passes FormData body through unchanged and does not set Content-Type', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch' as any).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
      url: 'http://test-api.com/test',
    } as Response);

    const formData = new FormData();
    formData.append('key', 'value');
    await api('/test', { method: 'POST', body: formData });

    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe(formData);
    const headers = init.headers instanceof Headers ? init.headers : new Headers(init.headers as HeadersInit);
    expect(headers.has('Content-Type')).toBe(false);

    fetchSpy.mockRestore();
  });

  it('passes Blob body through unchanged and sets appropriate Content-Type', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch' as any).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
      url: 'http://test-api.com/test',
    } as Response);

    const blob = new Blob(['test data'], { type: 'text/plain' });
    await api('/test', { method: 'POST', body: blob });

    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe(blob);
    const headers = init.headers instanceof Headers ? init.headers : new Headers(init.headers as HeadersInit);
    expect(headers.get('Content-Type')).toBe('text/plain');

    fetchSpy.mockRestore();
  });

  it('passes URLSearchParams body through unchanged and sets Content-Type', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch' as any).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
      url: 'http://test-api.com/test',
    } as Response);

    const params = new URLSearchParams('key=value&foo=bar');
    await api('/test', { method: 'POST', body: params });

    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe(params);
    const headers = init.headers instanceof Headers ? init.headers : new Headers(init.headers as HeadersInit);
    expect(headers.get('Content-Type')).toBe('application/x-www-form-urlencoded');

    fetchSpy.mockRestore();
  });
});

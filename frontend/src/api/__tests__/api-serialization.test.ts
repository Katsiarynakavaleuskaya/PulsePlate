// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach, type MockInstance } from 'vitest';
import { api, setApiClientDependencies, UnauthorizedError } from '../client';
import { createPremiumEndpoint } from '../premium/types';

const nativeBodies = [
  {
    name: 'FormData',
    create: () => {
      const body = new FormData();
      body.append('value', 'synthetic');
      return body;
    },
  },
  { name: 'Blob', create: () => new Blob(['synthetic']) },
  { name: 'ArrayBuffer', create: () => new ArrayBuffer(4) },
  {
    name: 'ReadableStream',
    create: () => new ReadableStream({ start: controller => controller.close() }),
  },
  {
    name: 'callable arrayBuffer object',
    create: () => ({ arrayBuffer: vi.fn(async () => new ArrayBuffer(0)), value: 'synthetic' }),
  },
];

describe('API Body Serialization', () => {
  let fetchSpy: MockInstance<typeof fetch>;

  beforeEach(() => {
    vi.stubEnv('VITE_API_BASE', 'http://test-api.com');
    setApiClientDependencies({
      getStoredApiKey: () => null,
      clearStoredApiKey: vi.fn(),
      apiBase: 'http://test-api.com',
    });
    fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    setApiClientDependencies(null);
  });

  function lastRequest(): RequestInit {
    const [, init] = fetchSpy.mock.calls[fetchSpy.mock.calls.length - 1]!;
    expect(init).toBeDefined();
    return init as RequestInit;
  }

  it.each([
    { name: 'ordinary object', create: () => ({ a: 1, b: 'x' }), json: '{"a":1,"b":"x"}' },
    { name: 'array', create: () => [1, 'x'], json: '[1,"x"]' },
    {
      name: 'null-prototype object',
      create: () => Object.assign(Object.create(null), { a: 1, b: 'x' }),
      json: '{"a":1,"b":"x"}',
    },
  ])('serializes $name to exact JSON with Content-Type', async ({ create, json }) => {
    await api('/test', { method: 'POST', body: create() });
    const init = lastRequest();
    expect(init.body).toBe(json);
    expect(new Headers(init.headers).get('Content-Type')).toBe('application/json');
    expect(init.credentials).toBe('include');
  });

  it('does not set Content-Type for GET without body', async () => {
    await api('/ping', { method: 'GET' });
    const init = lastRequest();
    expect(init.body).toBeUndefined();
    expect(new Headers(init.headers).has('Content-Type')).toBe(false);
  });

  it.each([null, undefined])('preserves a %s body without synthesized JSON headers', async body => {
    await api('/test', { method: 'POST', body });
    const init = lastRequest();
    expect(init.body).toBe(body);
    expect(new Headers(init.headers).has('Content-Type')).toBe(false);
  });

  it.each(nativeBodies)('preserves $name identity without synthesized JSON headers', async ({ create }) => {
    const body = create();
    await api('/test', { method: 'POST', body });
    const init = lastRequest();
    expect(init.body).toBe(body);
    expect(new Headers(init.headers).has('Content-Type')).toBe(false);
  });

  it('does not invoke the callable arrayBuffer property while selecting transport', async () => {
    const arrayBuffer = vi.fn(async () => new ArrayBuffer(0));
    const body = { arrayBuffer, value: 'synthetic' };
    await api('/test', { method: 'POST', body });
    expect(lastRequest().body).toBe(body);
    expect(arrayBuffer).not.toHaveBeenCalled();
  });

  it.each([
    { name: 'native body', create: () => new Blob(['synthetic']) },
    { name: 'JSON object', create: () => ({ a: 1 }) },
  ])('preserves caller Content-Type precedence for $name', async ({ create }) => {
    await api('/test', {
      method: 'POST',
      body: create(),
      headers: { 'content-type': 'application/custom', 'X-Synthetic': 'retained' },
    }, undefined, true);
    const headers = new Headers(lastRequest().headers);
    expect(headers.get('Content-Type')).toBe('application/custom');
    expect(headers.get('X-Synthetic')).toBe('retained');
  });

  it('forwards generic factory object, signal and canonical request options', async () => {
    const endpoint = createPremiumEndpoint<{ a: number }, { ok: boolean }>('/test');
    const controller = new AbortController();
    const onAuthError = vi.fn();
    await expect(endpoint({ a: 1 }, { signal: controller.signal, onAuthError })).resolves.toEqual({ ok: true });
    const [url] = fetchSpy.mock.calls[fetchSpy.mock.calls.length - 1]!;
    const init = lastRequest();
    expect(url).toBe('http://test-api.com/test');
    expect(init.method).toBe('POST');
    expect(init.body).toBe('{"a":1}');
    expect(init.signal).toBe(controller.signal);
    expect(init.credentials).toBe('include');
    expect(new Headers(init.headers).get('Content-Type')).toBe('application/json');
    expect(onAuthError).not.toHaveBeenCalled();
    controller.abort();
    expect(init.signal?.aborted).toBe(true);
  });

  it.each(nativeBodies)('keeps generic factory $name identity and explicit JSON header', async ({ create }) => {
    const body = create();
    const endpoint = createPremiumEndpoint<typeof body, { ok: boolean }>('/test');
    const controller = new AbortController();
    await endpoint(body, { signal: controller.signal });
    const init = lastRequest();
    expect(init.body).toBe(body);
    expect(init.signal).toBe(controller.signal);
    expect(new Headers(init.headers).get('Content-Type')).toBe('application/json');
  });

  it('forwards factory auth callbacks through the real API seam', async () => {
    fetchSpy.mockResolvedValueOnce(new Response('{}', {
      status: 403,
      headers: { 'Content-Type': 'application/json' },
    }));
    const endpoint = createPremiumEndpoint<{ a: number }, { ok: boolean }>('/test');
    const onAuthError = vi.fn();
    const controller = new AbortController();
    await expect(endpoint({ a: 1 }, { onAuthError, signal: controller.signal })).rejects.toBeInstanceOf(UnauthorizedError);
    expect(onAuthError).toHaveBeenCalledTimes(1);
    expect(onAuthError).toHaveBeenCalledWith(403, { clearApiKey: expect.any(Function) });
    expect(lastRequest().signal).toBe(controller.signal);
  });
});

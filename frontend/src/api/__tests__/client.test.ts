/** @vitest-environment jsdom */
import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { api, validateApiKey, getWeekPlan, isJsonString, setApiClientDependencies } from "../client";

const originalFetch = globalThis.fetch;
const originalLocation = window.location;
const fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>(async () =>
  new Response("{}", { status: 200, url: "http://test" })
);
(globalThis as any).fetch = fetchMock;

const originalEnv = { ...process.env };

beforeEach(() => {
  fetchMock.mockReset();
  vi.restoreAllMocks();
  setApiClientDependencies({
    getApiKey: () => undefined,
    clearApiKey: () => {},
    apiBase: "http://test-api.com",
  });
  Object.defineProperty(window, "location", {
    value: { ...originalLocation, replace: vi.fn() },
    writable: true,
  });
});

afterEach(() => {
  setApiClientDependencies(null);
  Object.defineProperty(window, "location", {
    value: originalLocation,
    writable: true,
  });
});

describe("isJsonString", () => {
  it("detects valid JSON", () => {
    expect(isJsonString('{"a":1}')).toBe(true);
    expect(isJsonString('[1,2,3]')).toBe(true);
  });

  it("rejects invalid or non-string", () => {
    expect(isJsonString("not json")).toBe(false);
    expect(isJsonString("{a:1}")).toBe(false);
    expect(isJsonString(123 as unknown as string)).toBe(false);
  });
});

describe("api client", () => {
  afterEach(() => {
    setApiClientDependencies(null);
  });

  it("throws when API base is missing", async () => {
    setApiClientDependencies({
      getApiKey: () => undefined,
      clearApiKey: () => {},
      apiBase: "",
    });

    await expect(api("/ping")).rejects.toThrow("VITE_API_BASE is not set");
  });

  it("adds API key header when available", async () => {
    setApiClientDependencies({
      getApiKey: () => "test-key",
      clearApiKey: () => {},
      apiBase: "http://test-api.com",
    });

    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200, url: "http://test" })
    );

    const response = await api("/secure", { method: "POST", body: JSON.stringify({}) });
    expect(response).toEqual({ ok: true });
    const [input, requestInit] = fetchMock.mock.calls[0];
    let headers: Headers;
    if (requestInit && (requestInit as RequestInit).headers) {
      headers = new Headers((requestInit as RequestInit).headers as HeadersInit);
    } else if (input instanceof Request) {
      headers = input.headers;
    } else {
      headers = new Headers();
    }
    expect(headers.get("X-API-Key")).toBe("test-key");
  });

  it("invokes onAuthError when server returns 401", async () => {
    const handler = vi.fn();
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        url: "http://test",
      })
    );

    await expect(api("/secure", { onAuthError: handler })).rejects.toThrow(
      "API key invalid or expired."
    );
    expect(handler).toHaveBeenCalledWith(401);
  });

  it("falls back to mock URL when network fails", async () => {
    fetchMock
      .mockRejectedValueOnce(new TypeError("Network down"))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ mock: true }), { status: 200, url: "/mock/bmr.json" })
      );

    const result = await api("/premium/bmr", { mockUrl: "/mock/bmr.json" });
    expect(result).toEqual({ mock: true });
  });
});

describe("validateApiKey", () => {
  it("returns false on failure", async () => {
    fetchMock.mockRejectedValueOnce(new Error("network"));
    const ok = await validateApiKey();
    expect(ok).toBe(false);
  });

  it("returns false when API base missing", async () => {
    setApiClientDependencies({
      getApiKey: () => undefined,
      clearApiKey: () => {},
      apiBase: "",
    });
    const ok = await validateApiKey();
    expect(ok).toBe(false);
  });
});

describe("getWeekPlan", () => {
  it("does not trigger handler on success", async () => {
    const handler = vi.fn();
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ days: [] }), { status: 200, url: "http://test" })
    );

    await getWeekPlan(handler);
    expect(handler).not.toHaveBeenCalled();
  });
});

afterEach(() => {
  setApiClientDependencies(null);
});

afterAll(() => {
  globalThis.fetch = originalFetch;
});

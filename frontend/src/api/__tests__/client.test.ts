import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { api } from "../client";
import * as logMod from "../../lib/analytics";

const originalFetch = globalThis.fetch;

beforeEach(() => {
  vi.resetAllMocks();
  vi.spyOn(logMod, "logError").mockImplementation(() => {});
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.clearAllMocks();
});

describe("api client auth", () => {
  it("resolves with data on successful response", async () => {
    const onAuthError = vi.fn();
    const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
    const url = "/premium/plate";
    const mockData = { calories: 2000, macros: { protein: 150, fat: 67, carbs: 250 } };

    // Mock fetch to return successful response
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockData),
      url: `${API_BASE}${url}`,
    } as unknown as Response);

    const result = await api(url, { method: "POST", body: {}, onAuthError });

    expect(result).toEqual(mockData);
    expect(onAuthError).not.toHaveBeenCalled();
    expect(logMod.logError).not.toHaveBeenCalled();
    expect(globalThis.fetch).toHaveBeenCalledWith(
      `${API_BASE}${url}`,
      expect.objectContaining({ method: "POST" })
    );
  });

  it("calls onAuthError + logs on 401", async () => {
    const onAuthError = vi.fn();
    const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
    const url = "/premium/plate";

    // Mock fetch to return 401
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      text: () => Promise.resolve(""),
      url: `${API_BASE}${url}`,
    } as unknown as Response);

    await expect(api(url, { method: "POST", body: {}, onAuthError })).rejects.toBeTruthy();
    expect(onAuthError).toHaveBeenCalledWith(401, expect.objectContaining({ clearApiKey: expect.any(Function) }));
    expect(logMod.logError).toHaveBeenCalled();
  });

  it("calls onAuthError + logs on 403", async () => {
    const onAuthError = vi.fn();
    const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
    const url = "/premium/plate";

    // Mock fetch to return 403
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      statusText: "Forbidden",
      text: () => Promise.resolve(""),
      url: `${API_BASE}${url}`,
    } as unknown as Response);

    await expect(api(url, { method: "POST", body: {}, onAuthError })).rejects.toBeTruthy();
    expect(onAuthError).toHaveBeenCalledWith(403, expect.objectContaining({ clearApiKey: expect.any(Function) }));
    expect(logMod.logError).toHaveBeenCalled();
  });

  it.each([
    [400, "Bad Request"],
    [500, "Internal Server Error"],
  ])("rejects and logs on %i status code", async (statusCode, statusText) => {
    const onAuthError = vi.fn();
    const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
    const url = "/premium/plate";

    // Mock fetch to return error status
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: statusCode,
      statusText,
      text: () => Promise.resolve("Error details"),
      url: `${API_BASE}${url}`,
    } as unknown as Response);

    await expect(api(url, { method: "POST", body: {}, onAuthError })).rejects.toThrow(`HTTP ${statusCode}: Error details`);
    expect(onAuthError).not.toHaveBeenCalled();
    expect(logMod.logError).toHaveBeenCalled();
  });

  it("rejects and logs when fetch rejects and no mockUrl provided", async () => {
    const onAuthError = vi.fn();
    const url = "/premium/plate";
    const networkError = new TypeError("Network request failed");

    // Mock fetch to reject
    globalThis.fetch = vi.fn().mockRejectedValue(networkError);

    await expect(api(url, { method: "POST", body: {}, onAuthError })).rejects.toThrow(networkError);
    expect(onAuthError).not.toHaveBeenCalled();
    expect(logMod.logError).toHaveBeenCalled();
  });

  it("falls back to mockUrl on network error when forceMock is false", async () => {
    const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
    const url = "/premium/plate";
    const mockUrl = "/mocks/premium/plate.json";

    // 1st call — network fails
    // 2nd call — mock succeeds
    globalThis.fetch = vi.fn()
      .mockRejectedValueOnce(new TypeError("Network down"))
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ ok: true }),
        url: mockUrl,
      } as unknown as Response);

    const res = await api(url, { method: "POST", body: {}, mockUrl, forceMock: false });
    expect(res).toEqual({ ok: true });

    // Check call order
    expect(globalThis.fetch).toHaveBeenNthCalledWith(
      1,
      `${API_BASE}${url}`,
      expect.objectContaining({ method: "POST" })
    );
    expect(globalThis.fetch).toHaveBeenNthCalledWith(
      2,
      mockUrl,
      expect.objectContaining({ method: "POST" })
    );
  });

  it("does not fall back when mockUrl is explicitly set to empty string", async () => {
    const url = "/premium/plate";
    const networkError = new TypeError("Network request failed");

    // Mock fetch to reject
    globalThis.fetch = vi.fn().mockRejectedValue(networkError);

    // When mockUrl is explicitly set to empty string, should not try to use automatic mock
    await expect(api(url, { method: "POST", body: {}, mockUrl: "", forceMock: false })).rejects.toThrow(networkError);

    // Should only call fetch once (the primary request), not the mock fallback
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });
});

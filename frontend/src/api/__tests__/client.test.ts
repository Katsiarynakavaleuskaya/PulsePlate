/** @vitest-environment jsdom */
import { describe, expect, it, beforeEach, vi } from "vitest";
import { api, API_BASE } from "../client";
import * as analytics from "../../lib/analytics";

const originalFetch = globalThis.fetch;

describe("api client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    globalThis.fetch = vi.fn();
  });

  it("invokes onAuthError and logs when 401 returned", async () => {
    const logSpy = vi.spyOn(analytics, "logError").mockImplementation(() => {});
    const onAuthError = vi.fn();

    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 401,
      url: "",
      text: () => Promise.resolve(""),
    } as Response);

    await expect(api("/premium/bmr", { method: "POST", body: "{}", onAuthError })).rejects.toThrow();

    expect(onAuthError).toHaveBeenCalledWith(401, expect.objectContaining({ clearApiKey: expect.any(Function) }));
    expect(logSpy).toHaveBeenCalled();
  });

  it("returns undefined for 204 No Content responses", async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 204,
      url: "",
      text: () => Promise.resolve(""),
    } as Response);

    const result = await api("/some-endpoint", { method: "GET" });
    expect(result).toBeUndefined();
  });

  it("falls back to mockUrl when network request fails", async () => {
    const fetchSpy = globalThis.fetch as unknown as ReturnType<typeof vi.fn>;

    fetchSpy
      .mockRejectedValueOnce(new TypeError("Network down"))
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        url: "/mock/bmr.json",
        json: () => Promise.resolve({ ok: true }),
      } as Response);

    const result = await api("/premium/bmr", { mockUrl: "/mock/bmr.json" });

    expect(result).toEqual({ ok: true });
    expect(fetchSpy).toHaveBeenNthCalledWith(1, `${API_BASE}/premium/bmr`, expect.any(Object));
    expect(fetchSpy).toHaveBeenNthCalledWith(2, "/mock/bmr.json", expect.any(Object));
  });
});

afterAll(() => {
  globalThis.fetch = originalFetch;
});

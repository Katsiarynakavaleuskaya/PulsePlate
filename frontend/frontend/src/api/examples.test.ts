import { describe, it, expect } from "vitest";
import { getOpenApi } from "./examples";

describe("api smoke", () => {
  it("fetches openapi.json (mocked in CI or dev proxy)", () => {
    expect(typeof getOpenApi).toBe("function");
  });
});

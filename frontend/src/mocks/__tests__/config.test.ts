import { describe, it, expect } from "vitest";
import { getMockUrl, MOCK_MAPPINGS } from "../config";

describe("mock config", () => {
  it("should have correct mappings", () => {
    expect(MOCK_MAPPINGS).toHaveLength(3);
    expect(MOCK_MAPPINGS[0]).toEqual({
      pattern: "/premium/bmr",
      mockPath: "/mock/bmr.json",
    });
    expect(MOCK_MAPPINGS[1]).toEqual({
      pattern: "/premium/plate",
      mockPath: "/mock/plate.json",
    });
    expect(MOCK_MAPPINGS[2]).toEqual({
      pattern: "/plan/week",
      mockPath: "/mock/week.json",
    });
  });

  it("should return correct mock URLs for matching patterns", () => {
    expect(getMockUrl("/premium/bmr")).toBe("/mock/bmr.json");
    expect(getMockUrl("/api/v1/premium/bmr")).toBe("/mock/bmr.json");
    expect(getMockUrl("/premium/plate")).toBe("/mock/plate.json");
    expect(getMockUrl("/plan/week")).toBe("/mock/week.json");
  });

  it("should return null for non-matching patterns", () => {
    expect(getMockUrl("/some/other/path")).toBeNull();
    expect(getMockUrl("/premium/unknown")).toBeNull();
    expect(getMockUrl("")).toBeNull();
  });

  it("should match first pattern in order", () => {
    // If we had overlapping patterns, first match should win
    // This is a hypothetical test - current patterns don't overlap
    expect(getMockUrl("/premium/bmr")).toBe("/mock/bmr.json");
  });
});

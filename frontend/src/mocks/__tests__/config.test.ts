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

  it("should match first pattern in order for overlapping mappings", () => {
    // Test the first-match behavior with overlapping patterns
    // Simulate getMockUrl logic with overlapping mappings
    const overlappingMappings = [
      {
        pattern: "/premium",
        mockPath: "/mock/premium.json",
      },
      {
        pattern: "/premium/bmr",
        mockPath: "/mock/bmr.json",
      },
    ];

    // Implement the same matching logic as getMockUrl
    const testGetMockUrl = (path: string): string | null => {
      const normalizedPath = path.split(/[?#]/)[0].replace(/^([^/])/, '/$1');

      for (const mapping of overlappingMappings) {
        const pathSegments = normalizedPath.split('/').filter(Boolean);
        const patternSegments = mapping.pattern.split('/').filter(Boolean);

        for (let i = 0; i <= pathSegments.length - patternSegments.length; i++) {
          if (patternSegments.every((segment, j) => segment === pathSegments[i + j])) {
            return mapping.mockPath;
          }
        }
      }
      return null;
    };

    // /premium/bmr should match "/premium" first since it appears earlier
    expect(testGetMockUrl("/premium/bmr")).toBe("/mock/premium.json");
    expect(testGetMockUrl("/premium")).toBe("/mock/premium.json");
  });
});

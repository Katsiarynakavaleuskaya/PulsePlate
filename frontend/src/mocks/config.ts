// RU: Центральная конфигурация моков для API эндпоинтов.
// EN: Centralized mock configuration for API endpoints.

export interface MockMapping {
  /** Pattern to match against the API path */
  pattern: string;
  /** Mock file path (relative to public directory) */
  mockPath: string;
}

/**
 * Mapping of API route patterns to mock file paths.
 * Patterns are matched using String.includes() for simplicity.
 * Order matters - first match wins.
 */
export const MOCK_MAPPINGS: MockMapping[] = [
  {
    pattern: "/premium/bmr",
    mockPath: "/mock/bmr.json",
  },
  {
    pattern: "/premium/plate",
    mockPath: "/mock/plate.json",
  },
  {
    pattern: "/plan/week",
    mockPath: "/mock/week.json",
  },
];

/**
 * Finds the mock file path for a given API path.
 * @param path - The API path to match against
 * @returns The mock file path if a pattern matches, null otherwise
 */
export function getMockUrl(path: string): string | null {
  // Normalize path to ensure it starts with leading slash and remove query/hash
  const normalizedPath = path.split(/[?#]/)[0].replace(/^([^/])/, '/$1');

  for (const mapping of MOCK_MAPPINGS) {
    // Split both path and pattern into segments for precise matching
    const pathSegments = normalizedPath.split('/').filter(Boolean);
    const patternSegments = mapping.pattern.split('/').filter(Boolean);

    // Check if pattern segments appear consecutively in path segments
    if (patternSegments.length === 0) {
      continue;
    }

    // Sliding-window approach: iterate possible start indexes in pathSegments
    // and compare consecutive segments against patternSegments for exact match
    for (let i = 0; i <= pathSegments.length - patternSegments.length; i++) {
      if (patternSegments.every((segment, j) => segment === pathSegments[i + j])) {
        return mapping.mockPath;
      }
    }
  }
  return null;
}

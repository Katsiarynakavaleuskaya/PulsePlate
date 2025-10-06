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
  for (const mapping of MOCK_MAPPINGS) {
    if (path.includes(mapping.pattern)) {
      return mapping.mockPath;
    }
  }
  return null;
}

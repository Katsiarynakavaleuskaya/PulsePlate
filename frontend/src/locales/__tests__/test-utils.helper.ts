// Test utilities for locale validation

// Constants
export const MAX_ALLOWED_DUPLICATES = 50;
export const STRING_LENGTH_LIMITS = {
  default: 500,
  extended: 1000,
} as const;

// Helper functions
export const collectKeyPaths = (obj: unknown, prefix = ''): string[] => {
  if (obj === null || typeof obj !== 'object') return [];
  return Object.entries(obj).flatMap(([key, value]) => {
    const currentPath = prefix ? `${prefix}.${key}` : key;
    return [
      currentPath,
      ...collectKeyPaths(value, currentPath)
    ];
  });
};

export const getMaxLength = (path: string): number => {
  if (path.includes('legal') || path.includes('description') || path.includes('disclaimer')) {
    return STRING_LENGTH_LIMITS.extended;
  }
  return STRING_LENGTH_LIMITS.default;
};

export const checkLengths = (obj: any, path = ''): string[] => {
  const issues: string[] = [];
  const maxLength = getMaxLength(path);

  if (typeof obj === 'string') {
    if (obj.length < 1 || obj.length > maxLength) {
      const displayed = obj.length > 50 ? obj.substring(0, 50) + "..." : obj;
      issues.push(`${path}: Invalid length ${obj.length} (max: ${maxLength}) for "${displayed}"`);
    }
  } else if (typeof obj === 'object' && obj !== null) {
    for (const [key, value] of Object.entries(obj)) {
      issues.push(...checkLengths(value, path ? `${path}.${key}` : key));
    }
  }

  return issues;
};

// Test logger to avoid console.warn in CI
export class TestLogger {
  private logs: string[] = [];

  warn(message: string, ...args: any[]) {
    const serializedArgs = args.length > 0
      ? args.map(arg => typeof arg === 'string' ? arg : JSON.stringify(arg)).join(' ')
      : '';
    const logEntry = serializedArgs ? `${message} ${serializedArgs}` : message;
    this.logs.push(logEntry);
    // Only log to console in development
    if (process.env.NODE_ENV !== 'test') {
      console.warn(message, ...args);
    }
  }

  getLogs(): string[] {
    return [...this.logs];
  }

  clear() {
    this.logs = [];
  }
}
